"""
Orchestrator for T's local access module.
Handles: local_access_start, local_access_confirm, local_access_end, memory_inspect.

Flow:
  1. Safety checks (firewall, AV, connections) — warnings only
  2. Send confirmation prompt to Tauri
  3. Wait for local_access_confirm with confirmed=true
  4. Spawn elevated helper via UAC prompt
  5. Authenticate helper over TCP callback
  6. Stream extraction results as they arrive
  7. After extraction: stay alive so memory inspector keeps working
  8. Kill switch (local_access_end) cancels the task → cleanup runs in finally
"""

import asyncio
import json
import secrets
from typing import TYPE_CHECKING

from .safety     import run_checks
from .session    import new_session, end_session, get_session, is_active
from .escalation import spawn_elevated, create_callback_server

from core.logger import get_logger

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("local_access.orchestrator")


async def handle_start(client: "Client", msg: dict) -> None:
    """
    Handle local_access_start.
    Runs safety checks, sends confirmation prompt.
    """
    if is_active():
        await client.send({
            "type":  "local_access_error",
            "error": "A session is already active. Send local_access_end first.",
        })
        return

    checks   = await run_checks()
    warnings = [c for c in checks if c["status"] == "warn"]

    warn_note = ""
    if warnings:
        warn_note = "\n⚠ Warnings:\n" + "\n".join(f"  • {w['message']}" for w in warnings) + "\n"

    await client.send({
        "type":    "local_access_ready",
        "id":      msg.get("id", ""),
        "sources": [
            "LSASS (cached Windows credentials)",
            "SAM database (local account NTLM hashes)",
            "Windows Credential Manager",
            "Browser saved passwords (Chrome, Edge, Firefox)",
            "WiFi passwords (all saved networks)",
            "Environment variables (API keys, tokens)",
            "Scheduled tasks with embedded credentials",
            "Registry credential paths",
        ],
        "checks":       checks,
        "risk_summary": (
            "Requires admin (Windows UAC prompt will appear).\n"
            "LSASS dump may trigger Windows Defender — fallback method ready.\n"
            "All temp files are encrypted and deleted on session end.\n"
            "No data leaves this machine.\n"
            f"{warn_note}"
            "Type YES to proceed."
        ),
    })


async def handle_confirm(client: "Client", msg: dict) -> None:
    """Handle local_access_confirm from Tauri."""
    if not msg.get("confirmed", False):
        await client.send({"type": "local_access_cancelled"})
        return
    # Run session as a separate task so handle() returns immediately
    asyncio.create_task(_run_session(client), name="la_session")


async def handle_end(client: "Client", msg: dict) -> None:
    """Kill switch — end active session immediately."""
    ended = await end_session()
    await client.send({
        "type":    "local_access_ended",
        "message": "Session ended. All temp files deleted." if ended else "No active session.",
    })
    log.info(f"local_access session ended by client {client.id}")


async def handle_memory_inspect(client: "Client", msg: dict) -> None:
    """Forward a memory_inspect command to the active helper."""
    session = get_session()
    if not session or not session.active:
        await client.send({
            "type":  "local_access_error",
            "error": "No active session. Start a session first.",
        })
        return
    q = getattr(session, "_cmd_queue", None)
    if q is None:
        await client.send({"type": "local_access_error", "error": "Helper not ready yet."})
        return
    await q.put(msg)


# ─── Internal ─────────────────────────────────────────────────────────────────

async def _run_session(client: "Client") -> None:
    """
    Full session lifecycle:
    spawn → authenticate → extract → stay alive for memory inspect → cleanup.

    Cancellation-safe: kill switch sets session.active=False and closes writer,
    then cancels this task. CancelledError propagates to the finally block.
    """
    session = new_session()
    session._cmd_queue = asyncio.Queue()   # type: ignore
    session._task      = asyncio.current_task()  # type: ignore

    # ── Setup TCP callback server ────────────────────────────────────────────
    helper_ready: "asyncio.Future[tuple]" = asyncio.get_event_loop().create_future()

    async def _on_connect(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        if not helper_ready.done():
            helper_ready.set_result((reader, writer))

    port, server = await create_callback_server(_on_connect)
    token        = secrets.token_hex(16)

    # ── Spawn elevated helper via UAC ────────────────────────────────────────
    success = spawn_elevated(port, token)
    if not success:
        server.close()
        await server.wait_closed()
        await client.send({
            "type":  "local_access_error",
            "error": "UAC elevation cancelled or failed.",
        })
        return

    await client.send({
        "type":    "local_access_progress",
        "source":  "Session",
        "status":  "waiting_for_helper",
        "message": "UAC accepted — waiting for helper...",
    })

    # ── Wait for helper connection (30s) ──────────────────────────────────────
    try:
        reader, writer = await asyncio.wait_for(helper_ready, timeout=30.0)
    except asyncio.TimeoutError:
        server.close()
        await server.wait_closed()
        await client.send({
            "type":  "local_access_error",
            "error": "Helper did not connect within 30s.",
        })
        return

    server.close()   # only one connection needed

    # ── Authenticate helper ───────────────────────────────────────────────────
    hello = await _read_line(reader)
    if not hello or hello.get("token") != token:
        writer.close()
        await client.send({"type": "local_access_error", "error": "Helper auth failed."})
        return

    # ── Session is live ───────────────────────────────────────────────────────
    session.active  = True
    session._writer = writer   # type: ignore
    asyncio.create_task(_cmd_loop(session, writer), name="la_cmd_loop")

    _write(writer, {"type": "extract_all", "session_key": session.key.hex()})

    all_hashes:        list[str] = []
    full_output_parts: list[str] = []

    try:
        # ── Stream extraction results ─────────────────────────────────────────
        while True:
            msg_h = await asyncio.wait_for(_read_line(reader), timeout=120.0)
            if msg_h is None:
                break

            t = msg_h.get("type")

            if t == "progress":
                await client.send({
                    "type":   "local_access_progress",
                    "source": msg_h.get("source"),
                    "status": msg_h.get("status"),
                })

            elif t == "result":
                full_output_parts.append(
                    f"\n{'='*40}\n{msg_h.get('source','')}\n{'='*40}\n{msg_h.get('data','')}"
                )

            elif t == "hashes":
                all_hashes.extend(msg_h.get("hashes", []))

            elif t == "error":
                await client.send({
                    "type":   "local_access_progress",
                    "source": msg_h.get("source"),
                    "status": "failed",
                    "error":  msg_h.get("error"),
                })

            elif t == "memory_inspect_result":
                await client.send(msg_h)

            elif t == "done":
                break

            elif t == "fatal_error":
                await client.send({
                    "type":  "local_access_error",
                    "error": msg_h.get("error"),
                })
                break

        # ── Send results to client ────────────────────────────────────────────
        n = len(full_output_parts)
        await client.send({
            "type":         "local_access_summary",
            "chat_summary": _build_summary(n, all_hashes),
        })
        await client.send({
            "type": "local_access_full",
            "data": "\n".join(full_output_parts),
        })
        if all_hashes:
            await client.send({
                "type":   "local_access_hashes",
                "hashes": list(set(all_hashes)),
            })
        log.info(f"extraction complete — {n} sources, {len(all_hashes)} hashes")

        # ── Stay alive for memory inspection ──────────────────────────────────
        # _cmd_loop forwards memory_inspect commands to the helper.
        # We block here until session.kill() cancels this task.
        while session.active:
            await asyncio.sleep(0.5)

    except asyncio.TimeoutError:
        await client.send({
            "type":  "local_access_error",
            "error": "Helper timed out during extraction.",
        })

    except asyncio.CancelledError:
        pass   # kill switch fired — fall through to finally

    finally:
        # session.kill() closes the writer before cancelling this task.
        # If we arrive here without kill() (timeout / error path), close it ourselves.
        if getattr(session, "_writer", None) is not None:
            try:
                writer.close()
            except Exception:
                pass
            session._writer = None  # type: ignore
        session.active = False
        log.info("local_access session task exiting")


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _cmd_loop(session, writer: asyncio.StreamWriter) -> None:
    """Forward commands from the queue to the helper (memory_inspect etc.)."""
    while session.active:
        try:
            cmd = await asyncio.wait_for(session._cmd_queue.get(), timeout=1.0)
            _write(writer, cmd)
        except asyncio.TimeoutError:
            continue
        except Exception:
            break


async def _read_line(reader: asyncio.StreamReader) -> dict | None:
    """Read one newline-delimited JSON message from the reader."""
    try:
        line = await reader.readline()
        if not line:
            return None
        return json.loads(line.decode("utf-8").strip())
    except Exception:
        return None


def _write(writer: asyncio.StreamWriter, payload: dict) -> None:
    """Write one JSON line. Fire-and-forget — safe for small messages."""
    try:
        writer.write((json.dumps(payload) + "\n").encode())
    except Exception:
        pass


def _build_summary(n_sources: int, hashes: list[str]) -> str:
    hash_note = (
        f" {len(hashes)} NTLM hash(es) found — session open for hashcat." if hashes else ""
    )
    return (
        f"Extraction complete. {n_sources} source(s) processed.{hash_note} "
        "Full output in LOCAL ACCESS tab. Memory inspector is active. "
        "Type 'end session' or click ■ when done."
    )
