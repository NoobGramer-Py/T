"""
T Persistence Installer
Installs T brain as a Windows service + registers tray icon at login.

Run once as Administrator:
  python install.py

To uninstall:
  python install.py --uninstall
"""

import sys
import os
import pathlib
import subprocess
import argparse

BRAIN_DIR   = pathlib.Path(__file__).resolve().parent.parent
PYTHON_EXE  = sys.executable
SERVICE_PY  = BRAIN_DIR / "service" / "windows_service.py"
TRAY_PY     = BRAIN_DIR / "service" / "tray.py"
LOG_DIR     = pathlib.Path(os.environ.get("APPDATA", "C:/Users/Public")) / "T" / "logs"

# Registry key for startup tray icon
STARTUP_REG_KEY   = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_REG_VALUE = "T-Tray"


def _print(msg: str) -> None:
    print(f"  {msg}")


def _check_admin() -> bool:
    """Check if running as administrator."""
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _install_deps() -> None:
    _print("Installing Python dependencies...")
    deps = ["pywin32", "pystray", "pillow"]
    for dep in deps:
        result = subprocess.run(
            [PYTHON_EXE, "-m", "pip", "install", dep, "-q"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            _print(f"  ✓ {dep}")
        else:
            _print(f"  ✗ {dep} — {result.stderr.strip()[:80]}")

    # pywin32 post-install
    try:
        scripts = pathlib.Path(PYTHON_EXE).parent / "Scripts" / "pywin32_postinstall.py"
        if scripts.exists():
            subprocess.run([PYTHON_EXE, str(scripts), "-install"], capture_output=True)
    except Exception:
        pass


def _install_service() -> None:
    _print("Installing Windows service (TBrainService)...")
    result = subprocess.run(
        [PYTHON_EXE, str(SERVICE_PY), "install"],
        capture_output=True, text=True,
        cwd=str(BRAIN_DIR),
    )
    if result.returncode == 0 or "already installed" in (result.stdout + result.stderr).lower():
        _print("  ✓ Service installed")
        # Set restart-on-failure (3 restarts, then wait)
        subprocess.run([
            "sc", "failure", "TBrainService",
            "reset=", "86400",
            "actions=", "restart/5000/restart/5000/restart/10000",
        ], capture_output=True)
        _print("  ✓ Auto-restart on failure configured")
    else:
        _print(f"  ✗ Service install failed: {result.stderr.strip()[:120]}")


def _install_tray_startup() -> None:
    _print("Registering tray icon at login...")
    try:
        import winreg
        cmd = f'"{PYTHON_EXE}" "{TRAY_PY}"'
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_REG_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, STARTUP_REG_VALUE, 0, winreg.REG_SZ, cmd)
        _print("  ✓ Tray icon will start at login")
        _print(f"  Command: {cmd}")
    except Exception as e:
        _print(f"  ✗ Registry write failed: {e}")


def _create_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _print(f"  ✓ Log directory: {LOG_DIR}")


def _start_service() -> None:
    _print("Starting brain service...")
    result = subprocess.run(
        ["sc", "start", "TBrainService"],
        capture_output=True, text=True,
    )
    if result.returncode == 0 or "already" in result.stderr.lower():
        _print("  ✓ Service running")
    else:
        _print(f"  ✗ Could not start: {result.stderr.strip()[:80]}")


def _launch_tray() -> None:
    _print("Launching tray icon...")
    subprocess.Popen(
        [PYTHON_EXE, str(TRAY_PY)],
        creationflags=subprocess.CREATE_NO_WINDOW,
        cwd=str(BRAIN_DIR),
    )
    _print("  ✓ Tray icon active")


def _uninstall() -> None:
    print("\n  Uninstalling T persistence...\n")

    # Stop and remove service
    subprocess.run(["sc", "stop", "TBrainService"], capture_output=True)
    result = subprocess.run(
        [PYTHON_EXE, str(SERVICE_PY), "remove"],
        capture_output=True, text=True, cwd=str(BRAIN_DIR),
    )
    _print("✓ Service removed" if result.returncode == 0 else f"Service: {result.stderr.strip()[:60]}")

    # Remove tray startup
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, STARTUP_REG_VALUE)
        _print("✓ Tray startup entry removed")
    except Exception as e:
        _print(f"Tray startup: {e}")

    # Kill tray process
    subprocess.run(
        ["taskkill", "/F", "/FI", "WINDOWTITLE eq T-Assistant*"],
        capture_output=True,
    )
    _print("✓ Tray process stopped")
    print("\n  T persistence uninstalled.\n")


def install() -> None:
    print("\n╔══════════════════════════════════════╗")
    print("║      T — PERSISTENCE INSTALLER       ║")
    print("╚══════════════════════════════════════╝\n")

    if not _check_admin():
        print("  ⚠ WARNING: Not running as Administrator.")
        print("  Service install may fail. Right-click → Run as Administrator.\n")

    _create_log_dir()
    _install_deps()
    _install_service()
    _install_tray_startup()
    _start_service()
    _launch_tray()

    print("\n  ✓ T persistence installed successfully.")
    print("  Brain auto-starts on boot (Windows service).")
    print("  Tray icon appears at login.")
    print(f"  Logs: {LOG_DIR}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="T Persistence Installer")
    parser.add_argument("--uninstall", action="store_true", help="Remove persistence")
    args = parser.parse_args()

    if args.uninstall:
        _uninstall()
    else:
        install()
