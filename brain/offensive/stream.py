"""
Streaming helper for T's offensive module.
Pipes subprocess stdout/stderr to WebSocket chunk messages in real time.
Used when a tool needs to run locally on the brain host (not on the VM).
"""

import asyncio
import re
from typing import AsyncIterator
from core.logger import get_logger

log = get_logger("offensive.stream")

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHF]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


async def stream_subprocess(
    args: list[str],
    timeout: int = 300,
    cwd: str | None = None,
) -> AsyncIterator[str]:
    """
    Run a local subprocess and yield stdout+stderr lines as they arrive.
    Yields '[EXIT:<code>]' as the last item on non-zero exit.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )
    except FileNotFoundError:
        yield f"[ERROR] Command not found: {args[0]}"
        return
    except Exception as e:
        yield f"[ERROR] Failed to start process: {e}"
        return

    assert proc.stdout is not None
    buf = b""

    try:
        async with asyncio.timeout(timeout):
            while True:
                chunk = await proc.stdout.read(512)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line_b, buf = buf.split(b"\n", 1)
                    line = _strip_ansi(line_b.decode(errors="replace"))
                    if line:
                        yield line
            # flush remaining
            if buf:
                line = _strip_ansi(buf.decode(errors="replace"))
                if line:
                    yield line
    except asyncio.TimeoutError:
        proc.kill()
        yield f"[ERROR] Timed out after {timeout}s"
        return

    await proc.wait()
    if proc.returncode and proc.returncode != 0:
        yield f"[EXIT:{proc.returncode}]"
