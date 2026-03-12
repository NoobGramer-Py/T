"""
Elevated session lifecycle for T's local access module.
Tracks one active session at a time.
Kill switch terminates helper, cleans all temp files, resets state.
No auto-expiry — session lasts until Abdul ends it manually.
"""

import asyncio
import secrets
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from core.logger import get_logger
from .safety import cleanup_temp, make_session_key

if TYPE_CHECKING:
    from asyncio import subprocess as asyncio_subprocess

log = get_logger("local_access.session")


@dataclass
class LocalSession:
    id:          str
    key:         bytes
    helper_proc: "asyncio.subprocess.Process | None" = field(default=None, repr=False)
    active:      bool = False
    port:        int  = 0

    @classmethod
    def create(cls) -> "LocalSession":
        return cls(id=secrets.token_hex(8), key=make_session_key())

    def attach_helper(self, proc: "asyncio.subprocess.Process", port: int) -> None:
        self.helper_proc = proc
        self.port        = port
        self.active      = True
        log.info(f"session {self.id} — helper attached on port {port}")

    async def kill(self) -> None:
        """
        Kill switch: terminate helper process, clean all temp files, reset state.
        Safe to call multiple times.
        """
        self.active = False

        if self.helper_proc is not None:
            try:
                self.helper_proc.kill()
                await asyncio.wait_for(self.helper_proc.wait(), timeout=5.0)
                log.info(f"session {self.id} — helper process terminated")
            except ProcessLookupError:
                pass   # already gone
            except Exception as e:
                log.warning(f"session {self.id} — helper kill error: {e}")
            finally:
                self.helper_proc = None

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
