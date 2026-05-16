"""
Log rotation for T brain logs.
Keeps logs from growing unbounded — rotates at 5MB, keeps 5 archives.
Called automatically by the Windows service and watchdog.
"""

import os
import gzip
import shutil
import pathlib
from datetime import datetime

LOG_DIR      = pathlib.Path(os.environ.get("APPDATA", str(pathlib.Path.home()))) / "T" / "logs"
MAX_SIZE     = 5 * 1024 * 1024   # 5 MB
MAX_ARCHIVES = 5


def rotate_if_needed(log_path: pathlib.Path) -> bool:
    """Rotate a log file if it exceeds MAX_SIZE. Returns True if rotated."""
    if not log_path.exists():
        return False
    if log_path.stat().st_size < MAX_SIZE:
        return False

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    arch = log_path.with_suffix(f".{ts}.gz")

    with open(log_path, "rb") as f_in:
        with gzip.open(arch, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    # Truncate the original log
    log_path.write_bytes(b"")

    # Prune old archives
    archives = sorted(
        log_path.parent.glob(f"{log_path.stem}.*.gz"),
        key=lambda p: p.stat().st_mtime,
    )
    for old in archives[:-MAX_ARCHIVES]:
        old.unlink(missing_ok=True)

    return True


def rotate_all() -> None:
    """Rotate all T log files in LOG_DIR."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for log_file in LOG_DIR.glob("*.log"):
        if rotate_if_needed(log_file):
            print(f"Rotated: {log_file.name}")


if __name__ == "__main__":
    rotate_all()
