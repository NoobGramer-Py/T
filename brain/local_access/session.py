"""
Elevated session lifecycle for T's local access module.
Tracks one active session at a time.
Kill switch terminates helper, cleans all temp files, resets state.
No auto-expiry — session lasts until Abdul ends it manually.
"""

import asyncio
import secrets
from dataclasses import dataclass
from core.logger import get_logger
from .safety import cleanup_temp, make_session_key

log = get_logger("local_access.session")


@dataclass
class LocalSession:
    id:     str
    key:    bytes
    active: bool = False
    port:   int  = 0

    @classmethod
    def create(cls) -> "LocalSession":
        return cls(id=secrets.token_hex(8), key=make_session_key())

    async def kill(self) -> None:
        """
        Kill switch: close helper connection, cancel extraction task,
        clean all temp files, reset state.
        Safe to call multiple times.
        """
        self.active = False

        # Close the writer — sends EOF to helper which causes it to exit cleanly
        writer = getattr(self, "_writer", None)
        if writer is not None:
            try:
                writer.close()
            except Exception:
                pass
            self._writer = None  # type: ignore

        # Cancel the extraction/wait task if still running
        task = getattr(self, "_task", None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=3.0)
            except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                pass
            self._task = None  # type: ignore

        deleted = cleanup_temp()
        log.info(f"session {self.id} ended — {deleted} temp file(s) deleted")


# Global singleton — one active session at a time
_session: LocalSession | None = None


def get_session() -> LocalSession | None:
    return _session


def new_session() -> LocalSession:
    global _session
    _session = LocalSession.create()
    return _session


async def end_session() -> bool:
    """End the active session. Returns True if there was a session to end."""
    global _session
    if _session is None:
        return False
    await _session.kill()
    _session = None
    return True


def is_active() -> bool:
    return _session is not None and _session.active
