"""
Orchestrator for T's local access module.
Handles: local_access_start, local_access_confirm, local_access_end, memory_inspect.
Flow:
  1. Safety checks (firewall, AV, connections) — warnings only
  2. Show confirmation prompt to Abdul
  3. Wait for local_access_confirm with confirmed=true
  4. Spawn elevated helper via UAC prompt
  5. Connect to helper via TCP callback server
  6. Stream results to Tauri as they arrive
  7. Kill switch: local_access_end → end session immediately
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

# Per-client confirmation futures — keyed by client.id
_pending_confirms: dict[str, asyncio.Future] = {}


async def handle_start(client: "Client", msg: dict) -> None:
    """
    Handle local_access_start message.
    Runs safety checks, sends confirmation prompt to Tauri.
    """
    if is_active():
        await client.send({
            "type":    "local_access_error",
            "error":   "A session is already active. Send local_access_end first.",
        })
        return

    # Safety checks
    checks    = await run_checks()
    warnings  = [c for c in checks if c["status"] == "warn"]
    check_txt = "\n".join(f"  [{c['check']}] {c['message']}" for c in checks)

    sources = [
        "LSASS (cached Windows credentials)",
        "SAM database (local account NTLM hashes)",
        "Windows Credential Manager",
        "Browser saved passwords (Chrome, Edge, Firefox)",
        "WiFi passwords (all saved networks)",
        "Environment variables (API keys, tokens)",
        "Scheduled tasks with embedded credentials",
        "Registry credential paths",
    ]

    warn_note = ""
    if warnings:
        warn_note = "\n⚠ Warnings:\n" + "\n".join(f"  • {w['message']}" for w in warnings) + "\n"

    await client.send({
        "type":         "local_access_ready",
        "id":           msg.get("id", ""),
        "sources":      sources,
        "checks":       checks,
        "risk_summary": (
            "Requires admin (Windows UAC prompt will appear).\n"
            "LSASS dump may trigger Windows Defender — fallback method ready.\n"
            "All temp files are encrypted and deleted within 60s.\n"
            "No data leaves this machine.\n"
            f"{warn_note}"
            "Type YES to proceed."
        ),
    })


async def handle_confirm(client: "Client", msg: dict) -> None:
    """
    Handle local_access_confirm.
    If confirmed=true: spawn helper, connect, stream results.
    """
    fut = _pending_confirms.pop(client.id, None)
    if fut and not fut.done():
        fut.set_result(bool(msg.get("confirmed", False)))
        return

    # Not waiting on a future — this is the primary confirm after handle_start
    if not msg.get("confirmed", False):
        await client.send({"type": "local_access_cancelled"})
        return

    await _run_session(client, msg)


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
            "error": "No active elevated session. Start a session first.",
        })
        return
    # The helper connection is managed by _run_session.
    # We publish the request via a shared asyncio queue on the session object.
    if hasattr(session, "_cmd_queue"):
        await session._cmd_queue.put(msg)   # type: ignore
    else:
        await client.send({"type": "local_access_error", "error": "Helper not ready yet."})


# ─── Internal ─────────────────────────────────────────────────────────────────

async def _run_session(client: "Client", msg: dict) -> None:
    """Spawn helper, connect, stream all results, clean up."""
    session = new_session()
    session._cmd_queue = asyncio.Queue()   # type: ignore

    # Create callback TCP server
    port, server = await create_callback_server()

    # Override connection handler now that we have session context
    helper_conn_future: asyncio.Future = asyncio.get_event_loop().create_future()

    async def _on_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        if not helper_conn_future.done():
            helper_conn_future.set_result((reader, writer))

    # Restart server with real handler
    server.close()
    await server.wait_closed()
    real_server = await asyncio.start_server(_on_connection, host="127.0.0.1", port=port)
    port = real_server.sockets[0].getsockname()[1]

    # Spawn elevated helper
    token   = secrets.token_hex(16)
    success = spawn_elevated(port, token)

    if not success:
        real_server.close()
        await real_server.wait_closed()
        await client.send({
            "type":  "local_access_error",
            "error": "UAC elevation cancelled or failed. Session not started.",
        })
        return

    await client.send({
        "type":    "local_access_progress",
        "source":  "Session",
        "status":  "waiting_for_helper",
        "message": "UAC accepted — waiting for helper to connect...",
    })

    # Wait for helper connection (up to 30s — UAC + process start time)
    try:
        reader, writer = await asyncio.wait_for(helper_conn_future, timeout=30.0)
    except asyncio.TimeoutError:
        real_server.close()
        await real_server.wait_closed()
        await client.send({
            "type":  "local_access_error",
            "error": "Helper did not connect within 30s. UAC may have been cancelled.",
        })
        return

    real_server.close()   # no more connections needed

    # Authenticate helper
    hello = await _read_line(reader)
    if not hello or hello.get("token") != token:
        writer.close()
        await client.send({"type": "local_access_error", "error": "Helper auth failed."})
        return

    session.active = True

    # Start command forwarding loop (memory inspect requests)
    asyncio.create_task(_cmd_loop(session, writer))

    # Send extraction command
    cmd = json.dumps({
        "type":        "extract_all",
        "session_key": session.key.hex(),
    }) + "\n"
    writer.write(cmd.encode())
    await writer.drain()

    # Stream results to client
    all_hashes: list[str] = []
    full_output_parts: list[str] = []

    try:
        while True:
            msg_from_helper = await asyncio.wait_for(_read_line(reader), timeout=120.0)
            if msg_from_helper is None:
                break

            t = msg_from_helper.get("type")

            if t == "progress":
                await client.send({
                    "type":   "local_access_progress",
                    "source": msg_from_helper.get("source"),
                    "status": msg_from_helper.get("status"),
                })

            elif t == "result":
                full_output_parts.append(
                    f"\n{'='*40}\n{msg_from_helper.get('source')}\n{'='*40}\n"
                    f"{msg_from_helper.get('data', '')}"
                )

            elif t == "hashes":
                all_hashes.extend(msg_from_helper.get("hashes", []))

            elif t == "error":
                await client.send({
                    "type":   "local_access_progress",
                    "source": msg_from_helper.get("source"),
                    "status": "failed",
                    "error":  msg_from_helper.get("error"),
                })

            elif t == "memory_inspect_result":
                await client.send(msg_from_helper)

            elif t == "done":
                break

            elif t == "fatal_error":
                await client.send({
                    "type":  "local_access_error",
                    "error": msg_from_helper.get("error"),
                })
                break

    except asyncio.TimeoutError:
        await client.send({
            "type":  "local_access_error",
            "error": "Helper timed out during extraction.",
        })
    finally:
        try:
            writer.write((json.dumps({"type": "end"}) + "\n").encode())
            await writer.drain()
        except Exception:
            pass
        writer.close()

    # Summarise and send to client
    n_sources = full_output_parts.count("=" * 40) // 2
    summary   = _build_summary(full_output_parts, all_hashes)

    await client.send({
        "type":         "local_access_summary",
        "chat_summary": summary,
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

    session.active = False
    log.info(f"extraction complete — {n_sources} sources, {len(all_hashes)} hashes")


async def _cmd_loop(session, writer: asyncio.StreamWriter) -> None:
    """Forward memory_inspect commands from the queue to the helper."""
    while session.active:
        try:
            cmd = await asyncio.wait_for(session._cmd_queue.get(), timeout=1.0)
            data = (json.dumps(cmd) + "\n").encode()
            writer.write(data)
            await writer.drain()
        except asyncio.TimeoutError:
            continue
        except Exception:
            break


async def _read_line(reader: asyncio.StreamReader) -> dict | None:
    """Read one JSON line from the stream reader."""
    try:
        line = await reader.readline()
        if not line:
            return None
        return json.loads(line.decode("utf-8").strip())
    except Exception:
        return None


def _build_summary(parts: list[str], hashes: list[str]) -> str:
    filled = [p for p in parts if p.strip() and "No " not in p and "Error" not in p]
    hash_note = f" {len(hashes)} NTLM hash(es) extracted — piping to hashcat." if hashes else ""
    return (
        f"Extraction complete. {len(parts)} sources processed.{hash_note} "
        "Full output in LOCAL ACCESS tab. Type 'end session' or click ■ to close the session."
    )
