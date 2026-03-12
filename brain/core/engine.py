import json
from typing import TYPE_CHECKING
from .llm import chat
from .logger import get_logger

if TYPE_CHECKING:
    from .ws_server import Client

log = get_logger("engine")

# Per-client conversation history: client_id → list of {role, content}
_histories: dict[str, list[dict]] = {}

# Per-client profile data synced from Tauri
_profiles: dict[str, dict] = {}


async def handle(client: "Client", raw: str) -> None:
    """Entry point for every message received from a Tauri client."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        log.warning(f"invalid JSON from {client.id}: {raw[:80]}")
        return

    msg_type = msg.get("type")

    if msg_type == "chat":
        await _handle_chat(client, msg)
    elif msg_type == "profile_sync":
        await _handle_profile_sync(client, msg)
    elif msg_type == "ping":
        await client.send({"type": "pong"})
    else:
        log.warning(f"unknown message type '{msg_type}' from {client.id}")


async def _handle_chat(client: "Client", msg: dict) -> None:
    msg_id  = msg.get("id", "")
    content = msg.get("content", "").strip()
    if not content:
        return

    history = _histories.setdefault(client.id, [])
    history.append({"role": "user", "content": content})

    # Keep last 40 turns (20 exchanges) in memory
    if len(history) > 40:
        _histories[client.id] = history[-40:]

    profile       = _profiles.get(client.id, {})
    anthropic_key = profile.get("anthropicKey", "")
    memory_ctx    = _build_memory_context(profile)

    # Signal visualizer to listening state
    await client.send({"type": "visualizer", "mode": "listening"})

    full_response = ""
    try:
        async for chunk in chat(history[:-1] + [{"role": "user", "content": content}],
                                memory_context=memory_ctx,
                                anthropic_key=anthropic_key):
            full_response += chunk
            await client.send({"type": "chat_chunk", "id": msg_id, "chunk": chunk})

        history.append({"role": "assistant", "content": full_response})
        await client.send({"type": "chat_done", "id": msg_id})
        await client.send({"type": "visualizer", "mode": "speaking"})

    except RuntimeError as e:
        log.error(f"LLM error: {e}")
        await client.send({"type": "chat_error", "id": msg_id, "error": str(e)})
        await client.send({"type": "visualizer", "mode": "idle"})


async def _handle_profile_sync(client: "Client", msg: dict) -> None:
    data = msg.get("data", {})
    _profiles[client.id] = data
    log.info(f"profile synced for {client.id}: name={data.get('name', '?')}")
    await client.send({"type": "profile_ack"})


def _build_memory_context(profile: dict) -> str:
    name = profile.get("name", "")
    notes = profile.get("notes", "")
    lines: list[str] = []
    if name:
        lines.append(f"The user's name is {name}.")
    if notes:
        lines.append(f"Notes: {notes}")
    if not lines:
        return ""
    return "[PERSISTENT MEMORY]\n" + "\n".join(lines) + "\n[END MEMORY]"


def on_disconnect(client_id: str) -> None:
    """Clean up history when a client disconnects."""
    _histories.pop(client_id, None)
    _profiles.pop(client_id, None)
