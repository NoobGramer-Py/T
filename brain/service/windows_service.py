"""
Windows Service wrapper for T's brain.
Registers brain/main.py as a proper Windows service that:
  - Starts automatically on boot (before login)
  - Self-heals via SCM restart policy
  - Writes logs to %APPDATA%/T/logs/

Usage:
  python windows_service.py install   -- install and start the service
  python windows_service.py remove    -- stop and remove the service
  python windows_service.py start     -- start the service
  python windows_service.py stop      -- stop the service
  python windows_service.py status    -- check if running
"""

import sys
import os
import time
import subprocess
import pathlib

# Service name and display name
SERVICE_NAME    = "TBrainService"
SERVICE_DISPLAY = "T — AI Core Brain"
SERVICE_DESC    = "T assistant brain — WebSocket server on ws://127.0.0.1:7891"

# Paths
BRAIN_DIR   = pathlib.Path(__file__).resolve().parent.parent
MAIN_PY     = BRAIN_DIR / "main.py"
PYTHON_EXE  = sys.executable
LOG_DIR     = pathlib.Path(os.environ.get("APPDATA", "C:/Users/Public")) / "T" / "logs"
LOG_FILE    = LOG_DIR / "service.log"


def _ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _log(msg: str) -> None:
    _ensure_log_dir()
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {msg}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass
    print(entry, end="")


# ── Windows Service class (pywin32) ────────────────────────────────────────────

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    import socket

    class TBrainWindowsService(win32serviceutil.ServiceFramework):
        _svc_name_         = SERVICE_NAME
        _svc_display_name_ = SERVICE_DISPLAY
        _svc_description_  = SERVICE_DESC

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.process    = None
            socket.setdefaulttimeout(60)

        def SvcStop(self):
            _log("Service stop requested")
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            _log(f"Service starting — brain: {MAIN_PY}")
            self._run_brain()

        def _run_brain(self):
            _ensure_log_dir()
            brain_log = LOG_DIR / "brain.log"

            while True:
                # Check stop signal
                rc = win32event.WaitForSingleObject(self.stop_event, 0)
                if rc == win32event.WAIT_OBJECT_0:
                    _log("Stop signal received — exiting")
                    break

                _log("Starting brain process...")
                try:
                    with open(brain_log, "a") as lf:
                        self.process = subprocess.Popen(
                            [PYTHON_EXE, str(MAIN_PY)],
                            cwd=str(BRAIN_DIR),
                            stdout=lf,
                            stderr=lf,
                            env={**os.environ, "T_SERVICE_MODE": "1"},
                        )

                    # Poll every second, check stop event
                    while self.process.poll() is None:
                        rc = win32event.WaitForSingleObject(self.stop_event, 1000)
                        if rc == win32event.WAIT_OBJECT_0:
                            _log("Stop during run — terminating brain")
                            self.process.terminate()
                            try:
                                self.process.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                self.process.kill()
                            return

                    exit_code = self.process.returncode
                    _log(f"Brain exited with code {exit_code} — restarting in 5s")

                except Exception as e:
                    _log(f"Brain launch error: {e} — retrying in 5s")

                # Wait 5 seconds before restart (check stop event)
                rc = win32event.WaitForSingleObject(self.stop_event, 5000)
                if rc == win32event.WAIT_OBJECT_0:
                    break

            _log("Service stopped cleanly")

    HAS_WIN32 = True

except ImportError:
    HAS_WIN32 = False


# ── CLI commands ───────────────────────────────────────────────────────────────

def _require_win32():
    if not HAS_WIN32:
        print("[ERROR] pywin32 not installed. Run: pip install pywin32")
        sys.exit(1)


def cmd_install():
    _require_win32()
    print(f"Installing service: {SERVICE_NAME}")
    win32serviceutil.InstallService(
        pythonClassString=f"{__name__}.TBrainWindowsService",
        serviceName=SERVICE_NAME,
        displayName=SERVICE_DISPLAY,
        description=SERVICE_DESC,
        startType=win32service.SERVICE_AUTO_START,
        exeName=PYTHON_EXE,
    )
    # Set restart-on-failure policy via sc.exe
    subprocess.run([
        "sc", "failure", SERVICE_NAME,
        "reset=", "60",
        "actions=", "restart/5000/restart/5000/restart/10000",
    ], capture_output=True)
    print("Service installed. Starting...")
    cmd_start()


def cmd_remove():
    _require_win32()
    try:
        cmd_stop()
    except Exception:
        pass
    print(f"Removing service: {SERVICE_NAME}")
    win32serviceutil.RemoveService(SERVICE_NAME)
    print("Service removed.")


def cmd_start():
    _require_win32()
    print(f"Starting service: {SERVICE_NAME}")
    win32serviceutil.StartService(SERVICE_NAME)
    print("Service started.")


def cmd_stop():
    _require_win32()
    print(f"Stopping service: {SERVICE_NAME}")
    win32serviceutil.StopService(SERVICE_NAME)
    print("Service stopped.")


def cmd_status() -> str:
    if not HAS_WIN32:
        return "unknown"
    try:
        status = win32serviceutil.QueryServiceStatus(SERVICE_NAME)
        state_map = {
            1: "stopped",
            2: "starting",
            3: "stopping",
            4: "running",
            5: "continue_pending",
            6: "pause_pending",
            7: "paused",
        }
        state = state_map.get(status[1], "unknown")
        print(f"Service {SERVICE_NAME}: {state}")
        return state
    except Exception as e:
        print(f"Service not found or error: {e}")
        return "not_installed"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: windows_service.py [install|remove|start|stop|status]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "install":  cmd_install()
    elif cmd == "remove": cmd_remove()
    elif cmd == "start":  cmd_start()
    elif cmd == "stop":   cmd_stop()
    elif cmd == "status": cmd_status()
    elif HAS_WIN32:
        # Called by SCM — run as service
        win32serviceutil.HandleCommandLine(TBrainWindowsService)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
