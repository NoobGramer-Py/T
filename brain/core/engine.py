import json
import asyncio
import re
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
_voice_active: set[str]           = set()
_pending_confirms: dict[str, asyncio.Future] = {}


# ─── Integration intent detection ─────────────────────────────────────────────

def _detect_integration(content: str) -> tuple[str, dict] | None:
    """
    Detect if a chat message is a direct integration request.
    Returns (integration_type, params) or None if it's a regular chat message.
    Fast keyword matching — no LLM call needed.
    """
    c = content.lower().strip()

    # Weather
    weather_m = re.search(
        r"weather\s+(?:in|for|at|of)?\s*(.+)|"
        r"(?:what(?:'s| is) it like|temperature|forecast)\s+(?:in|for|at)?\s*(.+)",
        c, re.IGNORECASE
    )
    if weather_m:
        loc = (weather_m.group(1) or weather_m.group(2) or "").strip().rstrip("?.")
        if loc:
            return ("weather", {"location": loc})

    # News
    if re.search(r"(latest|recent|today'?s?|current|breaking)\s+(news|headlines)", c) or \
       re.search(r"news\s+(about|on|regarding)\s+(.+)", c):
        news_m = re.search(r"news\s+(?:about|on|regarding)\s+(.+)", c)
        topic  = news_m.group(1).rstrip("?.") if news_m else ""
        return ("news", {"topic": topic})

    # Web search
    search_m = re.search(
        r"(?:search|look up|google|find|search for)\s+(?:for\s+)?(.+)", c, re.IGNORECASE
    )
    if search_m:
        query = search_m.group(1).rstrip("?.")
        return ("search", {"query": query})

    # Fetch URL
    url_m = re.search(r"(?:fetch|open|read|get|scrape)\s+(https?://\S+)", c, re.IGNORECASE)
    if url_m:
        return ("fetch_url", {"url": url_m.group(1)})

    # Launch app
    launch_m = re.search(
        r"(?:open|launch|start|run)\s+(?:up\s+)?([a-zA-Z0-9 +-]+?)(?:\s+(?:for me|please|now))?$",
        c, re.IGNORECASE
    )
    if launch_m:
        app_name = launch_m.group(1).strip()
        # Avoid matching "open http://..." (that's fetch_url) or very short strings
        if len(app_name) >= 2 and not app_name.startswith("http"):
            known_apps = {
                "chrome", "firefox", "edge", "vscode", "vs code", "notepad",
                "terminal", "calculator", "explorer", "file explorer", "spotify",
                "discord", "steam", "vlc", "obs", "wireshark", "burpsuite",
                "powershell", "cmd", "paint", "task manager",
            }
            if app_name.lower() in known_apps:
                return ("launch_app", {"name": app_name})

    # System info
    if re.search(r"(system|machine|pc|computer)\s+(info|information|specs|details|status)", c):
        return ("system_info", {})

    # Screenshot
    if re.search(r"(take|grab|capture)\s+(?:a\s+)?screenshot", c):
        return ("screenshot", {})

    # Clipboard read
    if re.search(r"(what('s| is) (?:in |on )?(?:my )?clipboard|read clipboard|get clipboard)", c):
        return ("get_clipboard", {})

    return None


async def _handle_integration(client: "Client", msg_id: str, kind: str, params: dict) -> bool:
    """
    Handle a detected integration request directly.
    Returns True if handled, False if should fall through to LLM.
    """
    try:
        from integrations.web import web_search, get_weather, fetch_url, get_news
        from integrations.system_control import (
            launch_app, get_clipboard, get_system_info, take_screenshot
        )

        if kind == "weather":
            result = await get_weather(params["location"])
        elif kind == "news":
            result = await get_news(params.get("topic", ""))
        elif kind == "search":
            result = await web_search(params["query"])
        elif kind == "fetch_url":
            result = await fetch_url(params["url"])
        elif kind == "launch_app":
            result = await launch_app(params["name"])
        elif kind == "system_info":
            result = await get_system_info()
        elif kind == "screenshot":
            result = await take_screenshot()
        elif kind == "get_clipboard":
            result = await get_clipboard()
        else:
            return False

        # Stream result as chat chunks
        # Chunk by line so it streams naturally
        lines = result.split("\n")
        for i, line in enumerate(lines):
            chunk = line + ("\n" if i < len(lines) - 1 else "")
            await client.send({"type": "chat_chunk", "id": msg_id, "chunk": chunk})

        await client.send({"type": "chat_done", "id": msg_id, "provider": "integration"})
        await client.send({"type": "visualizer", "mode": "speaking"})

        history = _histories.setdefault(client.id, [])
        history.append({"role": "assistant", "content": result})

        return True

    except Exception as e:
        log.warning(f"integration handler error kind={kind}: {e}")
        return False


async def handle(client: "Client", raw: str) -> None:
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        log.warning(f"invalid JSON from {client.id}: {raw[:80]}")
        return

    t = msg.get("type")
    if   t == "chat":                    await _handle_chat(client, msg)
    elif t == "agent":                   await _handle_agent(client, msg)
    elif t == "agent_confirm_response":  _handle_confirm_response(client, msg)
    elif t == "profile_sync":            await _handle_profile_sync(client, msg)
    elif t == "voice_start":             await _handle_voice_start(client)
    elif t == "voice_stop":              await _handle_voice_stop(client)
    elif t == "voice_enable":            _handle_voice_enable(client, msg)
    elif t == "local_access_start":      await _handle_local_access_start(client, msg)
    elif t == "local_access_confirm":    await _handle_local_access_confirm(client, msg)
    elif t == "local_access_end":        await _handle_local_access_end(client, msg)
    elif t == "memory_inspect":          await _handle_memory_inspect(client, msg)
    elif t == "set_reminder":            _handle_set_reminder(client, msg)
    elif t == "cancel_reminder":         _handle_cancel_reminder(client, msg)
    elif t == "ping":                    await client.send({"type": "pong"})
    else:
        log.warning(f"unknown message type '{t}' from {client.id}")


# ─── Chat ──────────────────────────────────────────────────────────────────────

async def _handle_chat(client: "Client", msg: dict) -> None:
    msg_id   = msg.get("id", "")
    content  = msg.get("content", "").strip()
    if not content:
        return

    history = _histories.setdefault(client.id, [])
    history.append({"role": "user", "content": content})
    if len(history) > 40:
        _histories[client.id] = history[-40:]

    # Observe for pattern-based suggestions (non-blocking)
    try:
        from proactive.engine import observe_message
        suggestion = observe_message(content)
        if suggestion:
            asyncio.create_task(
                client.send({"type": "proactive_alert", "severity": "info", "message": suggestion})
            )
    except Exception:
        pass

    profile  = _profiles.get(client.id, {})
    groq_key = profile.get("groqKey", "")

    await client.send({"type": "visualizer", "mode": "listening"})

    # Try direct integration handler first (weather, search, news, app launch, etc.)
    integration = _detect_integration(content)
    if integration:
        kind, params = integration
        log.info(f"integration detected  kind={kind}  params={params}")
        handled = await _handle_integration(client, msg_id, kind, params)
        if handled:
            if client.id in _voice_active:
                last = next(
                    (m["content"] for m in reversed(history) if m["role"] == "assistant"),
                    None,
                )
                if last:
                    from voice.pipeline import speak
                    asyncio.create_task(speak(client, last))
            return

    # LLM path
    memory_ctx    = build_context(content, profile)
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

        if client.id in _voice_active:
            from voice.pipeline import speak
            asyncio.create_task(speak(client, full_response))

    except RuntimeError as e:
        log.error(f"LLM error: {e}")
        await client.send({"type": "chat_error", "id": msg_id, "error": str(e)})
        await client.send({"type": "visualizer", "mode": "idle"})


# ─── Agent ─────────────────────────────────────────────────────────────────────

async def _handle_agent(client: "Client", msg: dict) -> None:
    msg_id = msg.get("id", "")
    task   = msg.get("task", "").strip()
    if not task:
        return

    profile  = _profiles.get(client.id, {})
    log.info(f"agent task  client={client.id}  task={task!r}")

    from agents.executor import run_agent
    try:
        answer = await run_agent(client, task, profile, msg_id)
        # Add agent result to conversation history as an assistant message
        history = _histories.setdefault(client.id, [])
        history.append({"role": "user",      "content": f"[AGENT TASK] {task}"})
        history.append({"role": "assistant",  "content": answer})
    except Exception as e:
        log.error(f"agent error: {e}")
        await client.send({"type": "agent_error", "id": msg_id, "error": str(e)})


def _handle_confirm_response(client: "Client", msg: dict) -> None:
    fut = _pending_confirms.pop(client.id, None)
    if fut and not fut.done():
        fut.set_result(bool(msg.get("confirmed", False)))


# ─── Voice ─────────────────────────────────────────────────────────────────────

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


# ─── Memory ────────────────────────────────────────────────────────────────────

async def _extract_and_store(
    client: "Client", user_msg: str, assistant_msg: str, groq_key: str,
) -> None:
    try:
        facts = await extract(user_msg, assistant_msg, groq_key=groq_key)
        for fact in facts:
            upsert(fact["key"], fact["value"])
            log.info(f"memory saved  key={fact['key']!r}")
            await client.send({"type": "memory_saved", "key": fact["key"], "value": fact["value"]})
    except Exception as e:
        log.warning(f"memory extraction error: {e}")


# ─── Profile ───────────────────────────────────────────────────────────────────

async def _handle_profile_sync(client: "Client", msg: dict) -> None:
    data = msg.get("data", {})
    _profiles[client.id] = data
    log.info(f"profile synced for {client.id}: name={data.get('name', '?')}")
    await client.send({"type": "profile_ack"})


# ─── Cleanup ───────────────────────────────────────────────────────────────────

def on_disconnect(client_id: str) -> None:
    _histories.pop(client_id, None)
    _profiles.pop(client_id, None)
    _voice_active.discard(client_id)
    fut = _pending_confirms.pop(client_id, None)
    if fut and not fut.done():
        fut.cancel()
    from voice.pipeline import cleanup
    cleanup(client_id)


# ─── Local Access ─────────────────────────────────────────────────────────────

async def _handle_local_access_start(client: "Client", msg: dict) -> None:
    from local_access.orchestrator import handle_start
    await handle_start(client, msg)


async def _handle_local_access_confirm(client: "Client", msg: dict) -> None:
    from local_access.orchestrator import handle_confirm
    await handle_confirm(client, msg)


async def _handle_local_access_end(client: "Client", msg: dict) -> None:
    from local_access.orchestrator import handle_end
    await handle_end(client, msg)


async def _handle_memory_inspect(client: "Client", msg: dict) -> None:
    from local_access.orchestrator import handle_memory_inspect
    await handle_memory_inspect(client, msg)


# ─── Reminders ────────────────────────────────────────────────────────────────

def _handle_set_reminder(client: "Client", msg: dict) -> None:
    try:
        from proactive.engine import schedule_reminder
        schedule_reminder(
            alert_id=msg["id"],
            message=msg["message"],
            fire_at=float(msg["fire_at"]),
        )
    except Exception as e:
        log.warning(f"set_reminder error: {e}")


def _handle_cancel_reminder(client: "Client", msg: dict) -> None:
    try:
        from proactive.engine import cancel_reminder
        cancel_reminder(msg["id"])
    except Exception as e:
        log.warning(f"cancel_reminder error: {e}")
