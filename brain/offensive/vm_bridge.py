"""
VM Bridge for T's offensive module.
Controls the attack VM via VBoxManage and executes commands over SSH using paramiko.
Streams stdout in real-time back to the caller via an async queue.
"""

import asyncio
import os
import re
import shlex
import shutil
from typing import AsyncIterator, TYPE_CHECKING
from core.logger import get_logger

if TYPE_CHECKING:
    pass

log = get_logger("offensive.vm_bridge")


def _find_vboxmanage() -> str:
    """
    Resolve the full path to VBoxManage on Windows and Linux.
    Returns 'VBoxManage' (bare name) if already on PATH,
    otherwise returns the full path from known install locations.
    """
    # Already on PATH — fastest check
    if shutil.which("VBoxManage"):
        return "VBoxManage"

    # Common Windows install locations
    candidates = [
        r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
        r"C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe",
        os.path.expandvars(r"%PROGRAMFILES%\Oracle\VirtualBox\VBoxManage.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Oracle\VirtualBox\VBoxManage.exe"),
        # Linux
        "/usr/bin/VBoxManage",
        "/usr/local/bin/VBoxManage",
    ]
    for p in candidates:
        if os.path.isfile(p):
            log.info(f"VBoxManage found at: {p}")
            return p

    # Last resort — return bare name and let it fail with a clear error
    return "VBoxManage"


# Resolved once at import time
VBOXMANAGE = _find_vboxmanage()


class VMBridge:
    """
    Manages a single Linux attack VM:
      - VBoxManage for VM lifecycle (start / stop / snapshot / status)
      - paramiko SSH for command execution with real-time stdout streaming
    """

    def __init__(self) -> None:
        self._ssh: "paramiko.SSHClient | None" = None  # type: ignore[name-defined]
        self._config: dict = {}

    # ── Configuration ─────────────────────────────────────────────────────────

    def configure(self, vm_name: str, vm_ip: str, ssh_user: str,
                  ssh_key: str = "", ssh_pass: str = "") -> None:
        """Set VM connection parameters. Called from engine on profile sync."""
        self._config = {
            "vm_name":  vm_name.strip(),
            "vm_ip":    vm_ip.strip(),
            "ssh_user": ssh_user.strip(),
            "ssh_key":  ssh_key.strip(),
            "ssh_pass": ssh_pass.strip(),
        }
        # Drop any open connection so the next call re-connects with new config
        self._close_ssh()

    def _configured(self) -> bool:
        # Requires IP and user — either a key path OR a password is sufficient
        cfg = self._config
        has_auth = bool(cfg.get("ssh_key")) or bool(cfg.get("ssh_pass"))
        return bool(cfg.get("vm_ip")) and bool(cfg.get("ssh_user")) and has_auth

    # ── VM Lifecycle (VBoxManage) ──────────────────────────────────────────────

    async def vm_status(self) -> dict:
        """Return VM running state and SSH reachability."""
        if not self._config.get("vm_ip"):
            return {
                "running": False, "ssh_ok": False,
                "error": "VM not configured — set IP, user and password in Settings → VM",
            }

        # ── VBoxManage check (best-effort — may fail if VM name wrong) ────────
        running  = False
        vbox_err = ""
        if self._config.get("vm_name"):
            try:
                proc = await asyncio.create_subprocess_exec(
                    VBOXMANAGE, "showvminfo", self._config["vm_name"], "--machinereadable",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                out, err = await asyncio.wait_for(proc.communicate(), timeout=10)
                text = out.decode(errors="replace")
                running  = 'VMState="running"' in text
                vbox_err = err.decode(errors="replace").strip() if not running else ""
            except FileNotFoundError:
                vbox_err = "VBoxManage not found"
            except asyncio.TimeoutError:
                vbox_err = "VBoxManage timed out"
            except Exception as e:
                vbox_err = str(e)

        # ── SSH check — always attempt if we have credentials ─────────────────
        ssh_ok  = False
        ssh_err = ""
        if self._configured():
            ssh_ok, ssh_err = await self._check_ssh_verbose()
        else:
            missing = []
            if not self._config.get("vm_ip"):      missing.append("IP")
            if not self._config.get("ssh_user"):   missing.append("SSH user")
            if not self._config.get("ssh_pass") and not self._config.get("ssh_key"):
                missing.append("SSH password or key")
            ssh_err = f"Missing: {', '.join(missing)}"

        message = ssh_err or vbox_err or ""

        return {
            "running":  running,
            "ssh_ok":   ssh_ok,
            "vm_ip":    self._config.get("vm_ip",   ""),
            "vm_name":  self._config.get("vm_name", ""),
            "message":  message,
        }

    async def vm_start(self) -> str:
        """Start the VM headless."""
        if not self._config.get("vm_name"):
            return "[ERROR] VM name not configured"
        try:
            proc = await asyncio.create_subprocess_exec(
                VBOXMANAGE, "startvm", self._config["vm_name"], "--type", "headless",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=30)
            if proc.returncode == 0:
                log.info(f"VM started: {self._config['vm_name']}")
                return f"VM '{self._config['vm_name']}' starting. SSH will be available in ~30 seconds."
            return f"[ERROR] {err.decode(errors='replace').strip()}"
        except FileNotFoundError:
            return "[ERROR] VBoxManage not found"
        except asyncio.TimeoutError:
            return "[ERROR] VM start timed out"
        except Exception as e:
            return f"[ERROR] {e}"

    async def vm_stop(self) -> str:
        """Power off the VM gracefully (ACPI shutdown)."""
        if not self._config.get("vm_name"):
            return "[ERROR] VM name not configured"
        self._close_ssh()
        try:
            proc = await asyncio.create_subprocess_exec(
                VBOXMANAGE, "controlvm", self._config["vm_name"], "acpipowerbutton",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=15)
            if proc.returncode == 0:
                return f"VM '{self._config['vm_name']}' shutting down."
            return f"[ERROR] {err.decode(errors='replace').strip()}"
        except Exception as e:
            return f"[ERROR] {e}"

    async def vm_snapshot(self, name: str) -> str:
        """Take a named snapshot of the current VM state."""
        if not self._config.get("vm_name"):
            return "[ERROR] VM name not configured"
        try:
            proc = await asyncio.create_subprocess_exec(
                VBOXMANAGE, "snapshot", self._config["vm_name"], "take", name,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            _, err = await asyncio.wait_for(proc.communicate(), timeout=60)
            if proc.returncode == 0:
                return f"Snapshot '{name}' created."
            return f"[ERROR] {err.decode(errors='replace').strip()}"
        except Exception as e:
            return f"[ERROR] {e}"

    async def vm_restore(self, name: str) -> str:
        """Restore VM to a named snapshot."""
        if not self._config.get("vm_name"):
            return "[ERROR] VM name not configured"
        self._close_ssh()
        try:
            proc = await asyncio.create_subprocess_exec(
                VBOXMANAGE, "snapshot", self._config["vm_name"], "restore", name,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            _, err = await asyncio.wait_for(proc.communicate(), timeout=30)
            if proc.returncode == 0:
                return f"VM restored to snapshot '{name}'."
            return f"[ERROR] {err.decode(errors='replace').strip()}"
        except Exception as e:
            return f"[ERROR] {e}"

    # ── SSH Execution ──────────────────────────────────────────────────────────

    async def run(self, command: str, timeout: int = 300) -> AsyncIterator[str]:
        """
        Execute a shell command on the VM over SSH.
        Yields stdout lines in real-time. Final line is empty string on success,
        or '[EXIT:<code>]' on non-zero exit.
        """
        if not self._configured():
            yield "[ERROR] VM SSH not configured. Enter VM settings first."
            return

        try:
            import paramiko
        except ImportError:
            yield "[ERROR] paramiko not installed. Run: pip install paramiko"
            return

        ssh = await self._get_ssh(paramiko)
        if ssh is None:
            yield f"[ERROR] Cannot connect to VM at {self._config['vm_ip']}. Is it running?"
            return

        loop = asyncio.get_event_loop()
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        def _run_blocking() -> None:
            try:
                transport = ssh.get_transport()
                if transport is None or not transport.is_active():
                    loop.call_soon_threadsafe(queue.put_nowait, "[ERROR] SSH transport lost")
                    loop.call_soon_threadsafe(queue.put_nowait, None)
                    return

                chan = transport.open_session()
                chan.set_combine_stderr(True)   # merge stderr → stdout
                chan.exec_command(command)

                buf = ""
                while True:
                    if chan.recv_ready():
                        data = chan.recv(4096).decode(errors="replace")
                        data = _strip_ansi(data)
                        buf += data
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            loop.call_soon_threadsafe(queue.put_nowait, line)
                    elif chan.exit_status_ready():
                        if buf:
                            loop.call_soon_threadsafe(queue.put_nowait, buf)
                        code = chan.recv_exit_status()
                        if code != 0:
                            loop.call_soon_threadsafe(queue.put_nowait, f"[EXIT:{code}]")
                        break
                    else:
                        import time
                        time.sleep(0.05)

                chan.close()
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, f"[ERROR] {e}")
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        fut = loop.run_in_executor(None, _run_blocking)

        try:
            async with asyncio.timeout(timeout):
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    yield item
        except asyncio.TimeoutError:
            yield f"[ERROR] Command timed out after {timeout}s"
        finally:
            fut.cancel()

    async def check_tool(self, tool_name: str) -> bool:
        """Return True if the tool binary exists on the VM."""
        found = False
        async for line in self.run(f"which {shlex.quote(tool_name)} 2>/dev/null", timeout=10):
            if line.strip() and not line.startswith("["):
                found = True
        return found

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _get_ssh(self, paramiko) -> "paramiko.SSHClient | None":
        """Return existing SSH client or create a new one."""
        if self._ssh is not None:
            t = self._ssh.get_transport()
            if t and t.is_active():
                return self._ssh
            self._ssh = None

        loop = asyncio.get_event_loop()
        try:
            client = await loop.run_in_executor(None, self._connect_blocking, paramiko)
            self._ssh = client
            return client
        except Exception as e:
            log.warning(f"SSH connect failed: {e}")
            return None

    def _connect_blocking(self, paramiko) -> "paramiko.SSHClient":
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh_key  = self._config.get("ssh_key",  "")
        ssh_pass = self._config.get("ssh_pass", "")

        connect_kwargs: dict = {
            "hostname":       self._config["vm_ip"],
            "username":       self._config["ssh_user"],
            "timeout":        10,
            "banner_timeout": 15,
            "auth_timeout":   10,
        }

        if ssh_key:
            # Key-based auth (preferred)
            connect_kwargs["key_filename"]   = ssh_key
            connect_kwargs["look_for_keys"]  = False
            connect_kwargs["allow_agent"]    = False
        elif ssh_pass:
            # Password auth
            connect_kwargs["password"]       = ssh_pass
            connect_kwargs["look_for_keys"]  = False
            connect_kwargs["allow_agent"]    = False
        else:
            # Try agent / default keys as last resort
            connect_kwargs["look_for_keys"]  = True
            connect_kwargs["allow_agent"]    = True

        client.connect(**connect_kwargs)
        return client

    async def _check_ssh_verbose(self) -> tuple[bool, str]:
        """Try SSH connection. Returns (success, error_message)."""
        try:
            import paramiko
        except ImportError:
            return False, "paramiko not installed — run: pip install paramiko"

        loop = asyncio.get_event_loop()
        try:
            client = await asyncio.wait_for(
                loop.run_in_executor(None, self._connect_blocking, paramiko),
                timeout=12,
            )
            self._ssh = client
            return True, ""
        except Exception as e:
            self._ssh = None
            err = str(e)
            # Give friendlier messages for common errors
            if "Authentication failed" in err:
                return False, f"SSH auth failed — check username/password in Settings"
            if "Connection refused" in err:
                return False, f"SSH connection refused — is SSH running on {self._config.get('vm_ip')}?"
            if "timed out" in err.lower() or "timeout" in err.lower():
                return False, f"SSH timed out — is {self._config.get('vm_ip')} reachable?"
            if "No route to host" in err or "Network unreachable" in err:
                return False, f"Cannot reach {self._config.get('vm_ip')} — check VM network adapter"
            return False, err

    async def _check_ssh(self) -> bool:
        ok, _ = await self._check_ssh_verbose()
        return ok

    def _close_ssh(self) -> None:
        if self._ssh:
            try:
                self._ssh.close()
            except Exception:
                pass
            self._ssh = None


# ── ANSI stripping ────────────────────────────────────────────────────────────

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHF]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


# ── Module-level singleton ─────────────────────────────────────────────────────

vm = VMBridge()
