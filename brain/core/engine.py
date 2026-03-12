import json
import asyncio
from typing import TYPE_CHECKING
from .llm import chat
from .logger import get_logger
from memory.injector import build_context
from memory.extractor import extract
from memory.store import upsert

if TYPE_CHECKING:
    from .ws_server import Client

log = get_logger("engine")

_histories: dict[str, list[dict]] = {}
_profiles:  dict[str, dict]       = {}
_voice_active: set[str]           = set()   # client IDs with voice enabled


async def handle(client: "Client", raw: str) -> None:
    """Entry point for every message received from a Tauri client."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        log.warning(f"invalid JSON from {client.id}: {raw[:80]}")
        return

    msg_type = msg.get("type")

    if   msg_type == "chat":          await _handle_chat(client, msg)
    elif msg_type == "profile_sync":  await _handle_profile_sync(client, msg)
    elif msg_type == "voice_start":   await _handle_voice_start(client)
    elif msg_type == "voice_stop":    await _handle_voice_stop(client)
    elif msg_type == "voice_enable":  _handle_voice_enable(client, msg)
    elif msg_type == "ping":          await client.send({"type": "pong"})
    else:
        log.warning(f"unknown message type '{msg_type}' from {client.id}")


async def _handle_chat(client: "Client", msg: dict) -> None:
    msg_id  = msg.get("id", "")
    content = msg.get("content", "").strip()
    if not content:
        return

    history = _histories.setdefault(client.id, [])
    history.append({"role": "user", "content": content})
    if len(history) > 40:
        _histories[client.id] = history[-40:]

    profile    = _profiles.get(client.id, {})
    groq_key   = profile.get("groqKey", "")
    memory_ctx = build_context(content, profile)

    await client.send({"type": "visualizer", "mode": "listening"})

    full_response = ""
    used_provider = "groq"
    try:
        async for chunk, provider in chat(
            history[:-1] + [{"role": "user", "content": content}],
            memory_context=memory_ctx,
            groq_key=groq_key,
        ):
            full_response += chunk
            used_provider  = provider
            await client.send({"type": "chat_chunk", "id": msg_id, "chunk": chunk})

        history.append({"role": "assistant", "content": full_response})
        await client.send({"type": "chat_done", "id": msg_id, "provider": used_provider})
        await client.send({"type": "visualizer", "mode": "speaking"})

        asyncio.create_task(_extract_and_store(client, content, full_response, groq_key))

        # Send TTS if voice is active for this client
        if client.id in _voice_active:
            from voice.pipeline import speak
            asyncio.create_task(speak(client, full_response))

    except RuntimeError as e:
        log.error(f"LLM error: {e}")
        await client.send({"type": "chat_error", "id": msg_id, "error": str(e)})
        await client.send({"type": "visualizer", "mode": "idle"})


async def _handle_voice_start(client: "Client") -> None:
    from voice.pipeline import handle_voice_start
    await handle_voice_start(client)


async def _handle_voice_stop(client: "Client") -> None:
    from voice.pipeline import handle_voice_stop
    await handle_voice_stop(client)


def _handle_voice_enable(client: "Client", msg: dict) -> None:
    enabled = bool(msg.get("enabled", False))
    if enabled:
        _voice_active.add(client.id)
    else:
        _voice_active.discard(client.id)
    log.info(f"voice {'enabled' if enabled else 'disabled'}  client={client.id}")


async def _extract_and_store(
    client:        "Client",
    user_msg:      str,
    assistant_msg: str,
    groq_key:      str,
) -> None:
    try:
        facts = await extract(user_msg, assistant_msg, groq_key=groq_key)
        for fact in facts:
            upsert(fact["key"], fact["value"])
            log.info(f"memory saved  key={fact['key']!r}")
            await client.send({"type": "memory_saved", "key": fact["key"], "value": fact["value"]})
    except Exception as e:
        log.warning(f"memory extraction error: {e}")


async def _handle_profile_sync(client: "Client", msg: dict) -> None:
    data = msg.get("data", {})
    _profiles[client.id] = data
    log.info(f"profile synced for {client.id}: name={data.get('name', '?')}")
    await client.send({"type": "profile_ack"})


def on_disconnect(client_id: str) -> None:
    _histories.pop(client_id, None)
    _profiles.pop(client_id, None)
    _voice_active.discard(client_id)
    from voice.pipeline import cleanup
    cleanup(client_id)
