"""
Watchdog for T's brain process.
Runs as a lightweight supervisor — if brain crashes it restarts it.
Used when running outside the Windows service (dev mode / Linux).
"""

import os
import sys
import time
import signal
import pathlib
import subprocess
import threading
from datetime import datetime

BRAIN_DIR  = pathlib.Path(__file__).resolve().parent.parent
MAIN_PY    = BRAIN_DIR / "main.py"
PYTHON_EXE = sys.executable
LOG_DIR    = pathlib.Path(os.environ.get("APPDATA", str(pathlib.Path.home() / ".local" / "share" / "T"))) / "T" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

RESTART_DELAY  = 5    # seconds before restarting after crash
MAX_RESTARTS   = 20   # within the window before giving up
RESTART_WINDOW = 120  # seconds — reset counter after this


class Watchdog:
    def __init__(self):
        self.process:       subprocess.Popen | None = None
        self.running:       bool  = True
        self.restart_count: int   = 0
        self.window_start:  float = time.time()
        self._lock = threading.Lock()

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [watchdog] {msg}"
        print(line, flush=True)
        try:
            with open(LOG_DIR / "watchdog.log", "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def _start_brain(self) -> subprocess.Popen:
        brain_log = open(LOG_DIR / "brain.log", "a", encoding="utf-8")
        proc = subprocess.Popen(
            [PYTHON_EXE, str(MAIN_PY)],
            cwd=str(BRAIN_DIR),
            stdout=brain_log,
            stderr=brain_log,
            env={**os.environ, "T_WATCHDOG": "1"},
        )
        self._log(f"Brain started — PID {proc.pid}")
        return proc

    def _reset_window_if_needed(self) -> None:
        now = time.time()
        if now - self.window_start > RESTART_WINDOW:
            self.restart_count = 0
            self.window_start  = now

    def run(self) -> None:
        self._log("Watchdog started")
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT,  self._handle_signal)

        self.process = self._start_brain()

        while self.running:
            try:
                exit_code = self.process.wait()
            except Exception:
                break

            if not self.running:
                break

            self._log(f"Brain exited (code {exit_code})")
            self._reset_window_if_needed()
            self.restart_count += 1

            if self.restart_count > MAX_RESTARTS:
                self._log(f"Too many restarts ({MAX_RESTARTS}) in {RESTART_WINDOW}s — giving up")
                break

            self._log(f"Restarting in {RESTART_DELAY}s (restart #{self.restart_count})")
            time.sleep(RESTART_DELAY)

            if self.running:
                self.process = self._start_brain()

        self._log("Watchdog exiting")

    def stop(self) -> None:
        self.running = False
        if self.process and self.process.poll() is None:
            self._log("Stopping brain process")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def _handle_signal(self, signum: int, _frame) -> None:
        self._log(f"Signal {signum} received — stopping")
        self.stop()


def main():
    watchdog = Watchdog()
    watchdog.run()


if __name__ == "__main__":
    main()
