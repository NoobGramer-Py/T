"""
T system tray icon for Windows.
Runs at user login via startup registry key.
Shows brain status, allows open/restart/stop from the tray.

Requirements: pip install pystray pillow
"""

import os
import sys
import time
import threading
import subprocess
import pathlib
import socket

# Add brain dir to path so we can import from it
BRAIN_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRAIN_DIR))

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

BRAIN_WS_HOST = "127.0.0.1"
BRAIN_WS_PORT = 7891
POLL_INTERVAL = 4   # seconds between status checks

# T app executable path (built version)
APP_EXE = pathlib.Path(os.environ.get("APPDATA", "")) / ".." / "Local" / "t-assistant" / "t-assistant.exe"


# ── Icon generation ────────────────────────────────────────────────────────────

def _make_icon(online: bool) -> "Image.Image":
    """Generate a 64x64 tray icon — cyan arc reactor when online, dim when offline."""
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy, r = size // 2, size // 2, size // 2 - 4

    if online:
        # Bright cyan outer ring
        for i in range(3):
            draw.ellipse(
                [cx - r + i, cy - r + i, cx + r - i, cy + r - i],
                outline=(0, 212, 255, 200 - i * 50),
            )
        # Inner glowing core
        draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=(0, 212, 255, 220))
        draw.ellipse([cx - 6,  cy - 6,  cx + 6,  cy + 6],  fill=(160, 244, 255, 255))
    else:
        # Dim grey — offline
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(60, 60, 80, 180))
        draw.ellipse([cx - 8,  cy - 8,  cx + 8,  cy + 8],  fill=(50, 50, 70, 180))

    return img


# ── Status check ───────────────────────────────────────────────────────────────

def _brain_online() -> bool:
    """Check if brain WebSocket is reachable."""
    try:
        with socket.create_connection((BRAIN_WS_HOST, BRAIN_WS_PORT), timeout=1):
            return True
    except OSError:
        return False


# ── Brain control ──────────────────────────────────────────────────────────────

def _start_brain() -> None:
    """Start the brain via Windows service or direct process."""
    try:
        # Try service first
        result = subprocess.run(
            ["sc", "query", "TBrainService"],
            capture_output=True, text=True,
        )
        if "TBrainService" in result.stdout:
            subprocess.run(["sc", "start", "TBrainService"], capture_output=True)
            return
    except Exception:
        pass

    # Fall back to direct launch
    subprocess.Popen(
        [sys.executable, str(BRAIN_DIR / "main.py")],
        cwd=str(BRAIN_DIR),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def _stop_brain() -> None:
    """Stop the brain service or process."""
    try:
        subprocess.run(["sc", "stop", "TBrainService"], capture_output=True)
    except Exception:
        pass
    # Also kill any direct python processes running main.py
    subprocess.run(
        ["taskkill", "/F", "/FI", f"IMAGENAME eq python.exe",
         "/FI", f"WINDOWTITLE eq *main.py*"],
        capture_output=True,
    )


def _open_ui() -> None:
    """Open the T main window."""
    # Try built exe first
    if APP_EXE.exists():
        subprocess.Popen([str(APP_EXE)])
        return
    # Dev mode — open via npm
    t_dir = BRAIN_DIR.parent
    subprocess.Popen(
        ["npm", "run", "tauri", "dev"],
        cwd=str(t_dir),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


# ── Tray app ───────────────────────────────────────────────────────────────────

class TrayApp:
    def __init__(self):
        self.online  = False
        self.icon    = None
        self._update_thread: threading.Thread | None = None

    def _update_status_loop(self) -> None:
        """Background thread — polls brain status and updates icon."""
        while self.icon and self.icon.visible:
            online = _brain_online()
            if online != self.online:
                self.online = online
                self._refresh_icon()
                self._refresh_menu()
            time.sleep(POLL_INTERVAL)

    def _refresh_icon(self) -> None:
        if self.icon:
            self.icon.icon = _make_icon(self.online)

    def _refresh_menu(self) -> None:
        if self.icon:
            self.icon.menu = self._build_menu()

    def _build_menu(self) -> "pystray.Menu":
        status_label = "● BRAIN ONLINE" if self.online else "○ BRAIN OFFLINE"
        status_color = "(running)" if self.online else "(stopped)"

        return pystray.Menu(
            pystray.MenuItem(
                f"T — AI Core  {status_color}",
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                status_label,
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open T",        lambda icon, item: _open_ui()),
            pystray.MenuItem("Restart Brain", lambda icon, item: self._restart()),
            pystray.MenuItem(
                "Stop Brain",
                lambda icon, item: self._stop(),
                enabled=self.online,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit Tray",     lambda icon, item: self._exit()),
        )

    def _restart(self) -> None:
        _stop_brain()
        time.sleep(2)
        _start_brain()
        time.sleep(2)
        self.online = _brain_online()
        self._refresh_icon()
        self._refresh_menu()

    def _stop(self) -> None:
        _stop_brain()
        self.online = False
        self._refresh_icon()
        self._refresh_menu()

    def _exit(self) -> None:
        if self.icon:
            self.icon.stop()

    def run(self) -> None:
        if not HAS_TRAY:
            print("[ERROR] pystray/Pillow not installed.")
            print("Run: pip install pystray pillow")
            sys.exit(1)

        self.online = _brain_online()
        self.icon   = pystray.Icon(
            name="T-Assistant",
            icon=_make_icon(self.online),
            title="T — AI Core",
            menu=self._build_menu(),
        )

        # Start status polling thread
        self._update_thread = threading.Thread(
            target=self._update_status_loop, daemon=True
        )
        self._update_thread.start()

        self.icon.run()


def main() -> None:
    app = TrayApp()
    app.run()


if __name__ == "__main__":
    main()
