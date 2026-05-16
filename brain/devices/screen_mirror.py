"""
Android screen mirroring for T — Phase 16.
Uses ADB wireless debugging (Android 11+) or TCP ADB to mirror the device screen.
Streams MJPEG frames over a WebSocket connection to the Devices panel.

Setup required on Android device (ONE TIME — done by device owner):
  Settings → Developer Options → Wireless Debugging → Enable
  Pair device using the pairing code T provides

No silent access. Device shows ADB notification while connected.
"""

import asyncio
import subprocess
import pathlib
import time
from typing import AsyncIterator, TYPE_CHECKING
from core.logger import get_logger
from devices.mobile import stream_subprocess

_PATH = "PATH=$PATH:$HOME/.local/bin:/usr/local/bin:/usr/lib/android-sdk/platform-tools "


def _adb_bin() -> str:
    """Resolve adb binary path — checks PATH, then where.exe, then glob, then common locations."""
    import shutil
    import subprocess
    import pathlib

    if shutil.which("adb"):
        return "adb"

    # Ask Windows where it is (handles winget, scoop, any installer)
    try:
        r = subprocess.run(
            ["where.exe", "adb"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            p = r.stdout.strip().splitlines()[0].strip()
            if p and pathlib.Path(p).exists():
                return p
    except Exception:
        pass

    # Glob through winget packages directory
    try:
        winget = pathlib.Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
        if winget.exists():
            hits = list(winget.glob("*PlatformTools*/platform-tools/adb.exe"))
            if hits:
                return str(hits[0])
    except Exception:
        pass

    # Fixed fallback locations
    for c in [
        r"C:\platform-tools\adb.exe",
        r"C:\Program Files\Android\platform-tools\adb.exe",
    ]:
        if pathlib.Path(c).exists():
            return c

    return "adb"

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("devices.screen_mirror")

# scrcpy args — no audio, no control (view only for screen share)
SCRCPY_VIEW_ONLY = [
    "scrcpy",
    "--no-audio",
    "--no-control",        # view only — cannot interact
    "--turn-screen-off",   # keep device screen off while mirroring (saves battery)
    "--stay-awake",
    "--max-fps", "15",     # 15fps — enough for screen view, low bandwidth
    "--bit-rate", "2M",
    "--window-title", "T — Screen Mirror",
]


# ── Wireless ADB pairing (Android 11+) ────────────────────────────────────────

async def pair_device(ip: str, pair_port: str, pair_code: str) -> AsyncIterator[str]:
    """
    Pair with an Android device using wireless debugging pairing code.
    The device owner generates this in Settings → Developer Options → Wireless Debugging.
    """
    yield f"[T] Pairing with {ip}:{pair_port} using code {pair_code}..."
    yield "Device owner must confirm pairing in Wireless Debugging settings."

    async for line in stream_subprocess(
        [_adb_bin(), "pair", f"{ip}:{pair_port}", pair_code],
        timeout=30,
    ):
        yield line


async def connect_wireless(ip: str, port: str = "5555") -> AsyncIterator[str]:
    """Connect to a wirelessly-paired Android device."""
    yield f"[T] Connecting to {ip}:{port}..."
    async for line in stream_subprocess(
        [_adb_bin(), "connect", f"{ip}:{port}"],
        timeout=15,
    ):
        yield line


async def list_connected() -> list[dict]:
    """List all ADB-connected Android devices."""
    devices: list[dict] = []
    try:
        result = subprocess.run(
            [_adb_bin(), "devices", "-l"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.splitlines()[1:]:
            line = line.strip()
            if not line or "offline" in line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serial = parts[0]
                model  = next((p.split(":")[1] for p in parts if p.startswith("model:")), "Unknown")
                devices.append({"serial": serial, "model": model, "status": "online"})
    except Exception as e:
        log.warning(f"adb devices failed: {e}")
    return devices


# ── Screen capture (single frame) ─────────────────────────────────────────────

async def capture_screenshot(serial: str) -> bytes | None:
    """Capture a single PNG screenshot from the device. Returns raw bytes."""
    try:
        result = await asyncio.create_subprocess_exec(
            _adb_bin(), "-s", serial, "exec-out", "screencap", "-p",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(result.communicate(), timeout=10)
        if result.returncode == 0 and stdout:
            return stdout
    except Exception as e:
        log.warning(f"screenshot failed: {e}")
    return None


# ── Live screen stream ─────────────────────────────────────────────────────────

async def stream_screen(
    client: "Client",
    serial: str,
    session_id: str,
    fps: int = 2,
) -> None:
    """
    Stream device screenshots to the frontend at `fps` frames per second.
    Each frame is sent as a base64 PNG via WebSocket.

    fps=2 is enough for screen monitoring — higher fps strains the device.
    The device ADB notification remains visible throughout.
    """
    import base64

    log.info(f"Screen stream started: serial={serial} fps={fps}")
    await client.send({
        "type":      "device_stream_started",
        "id":        session_id,
        "serial":    serial,
        "note":      "ADB connection active — device shows notification",
    })

    frame_interval = 1.0 / max(1, min(fps, 5))   # clamp 1–5 fps
    stop_key       = f"_stop_stream_{session_id}"

    # Check device is still connected before looping
    devices = await list_connected()
    if not any(d["serial"] == serial for d in devices):
        await client.send({
            "type":  "device_stream_error",
            "id":    session_id,
            "error": f"Device {serial} not connected",
        })
        return

    frame_n = 0
    while not getattr(client, stop_key, False):
        t_start = time.monotonic()

        png = await capture_screenshot(serial)
        if png is None:
            await client.send({
                "type":  "device_stream_error",
                "id":    session_id,
                "error": "Screenshot failed — device may have disconnected",
            })
            break

        b64 = base64.b64encode(png).decode()
        await client.send({
            "type":    "device_frame",
            "id":      session_id,
            "serial":  serial,
            "frame_n": frame_n,
            "data":    b64,        # base64 PNG
        })

        frame_n += 1
        elapsed = time.monotonic() - t_start
        sleep   = max(0.0, frame_interval - elapsed)
        await asyncio.sleep(sleep)

    log.info(f"Screen stream stopped: serial={serial} frames={frame_n}")
    await client.send({"type": "device_stream_stopped", "id": session_id})


async def stop_stream(client: "Client", session_id: str) -> None:
    """Signal the stream loop to stop."""
    setattr(client, f"_stop_stream_{session_id}", True)


# ── scrcpy launcher (optional — opens a desktop window on Kali) ───────────────

async def launch_scrcpy(serial: str) -> AsyncIterator[str]:
    """
    Launch scrcpy on the local machine for full-quality screen view.
    Opens a resizable window — requires a display (not headless).
    """
    yield f"[T] Launching scrcpy for device {serial}..."
    yield "A screen mirror window will open on your desktop."

    cmd = SCRCPY_VIEW_ONLY + ["--serial", serial]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        yield f"[T] scrcpy started (PID {proc.pid})"
        yield "Close the scrcpy window to stop mirroring."
    except FileNotFoundError:
        yield "[ERROR] scrcpy not found."
        yield "Install: sudo apt install scrcpy"
    except Exception as e:
        yield f"[ERROR] scrcpy launch failed: {e}"


# ── Setup instructions ─────────────────────────────────────────────────────────

def setup_instructions() -> list[str]:
    """Return step-by-step setup instructions shown to the device owner."""
    return [
        "STEP 1 — Enable Developer Options",
        "  Settings → About Phone → tap Build Number 7 times",
        "",
        "STEP 2 — Enable Wireless Debugging",
        "  Settings → Developer Options → Wireless Debugging → toggle ON",
        "",
        "STEP 3 — Pair with T",
        "  Wireless Debugging → Pair device with pairing code",
        "  Enter the IP, port and code shown there into T",
        "  Tap PAIR in T",
        "",
        "STEP 4 — Connect",
        "  Wireless Debugging → note the IP and port shown",
        "  Enter those into T and tap CONNECT",
        "",
        "NOTE: Your device will show an ADB notification while T is connected.",
        "      To disconnect: disable Wireless Debugging or tap DISCONNECT in T.",
    ]
