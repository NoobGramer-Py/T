"""
Privilege escalation for T's local access module.
Spawns helper.py as an elevated subprocess via standard Windows UAC prompt.
Brain stays running throughout — no WebSocket drop.
Communication: helper connects back to brain's local TCP server on a random port.
"""

import asyncio
import ctypes
import os
import sys
from pathlib import Path
from core.logger import get_logger

log = get_logger("local_access.escalation")

# Path to helper.py in the same package
_HELPER_PATH = Path(__file__).parent / "helper.py"


def is_admin() -> bool:
    """Return True if the current process is running with admin privileges."""
    if sys.platform != "win32":
        return os.getuid() == 0   # type: ignore[attr-defined]
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


async def create_callback_server() -> tuple[int, asyncio.Server]:
    """
    Create a local TCP server on a random port.
    Helper.py will connect back to this port after elevation.
    Returns (port, server).
    """
    server = await asyncio.start_server(
        lambda r, w: None,   # placeholder — replaced by orchestrator before accepting
        host="127.0.0.1",
        port=0,              # OS assigns a random available port
    )
    port = server.sockets[0].getsockname()[1]
    log.info(f"callback server listening on 127.0.0.1:{port}")
    return port, server


def spawn_elevated(port: int, token: str) -> bool:
    """
    Spawn helper.py as an elevated process via Windows UAC prompt (standard, visible).
    Returns True if ShellExecuteW reports success (>32), False otherwise.
    On non-Windows, logs a warning and returns False.
    """
    if sys.platform != "win32":
        log.warning("elevation not supported on this platform — Windows only")
        return False

    python_exe = sys.executable
    helper     = str(_HELPER_PATH)
    params     = f'"{helper}" --port {port} --token {token}'

    log.info(f"requesting elevation via UAC — spawning helper on port {port}")

    ret = ctypes.windll.shell32.ShellExecuteW(
        None,       # hwnd — no parent window
        "runas",    # operation — triggers UAC elevation dialog
        python_exe, # executable
        params,     # parameters
        None,       # working directory (inherit)
        1,          # SW_NORMAL — show normal window
    )
    success = int(ret) > 32
    if success:
        log.info("UAC elevation accepted — helper process launching")
    else:
        log.warning(f"UAC elevation failed or cancelled — ShellExecuteW returned {ret}")
    return success
