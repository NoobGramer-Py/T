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
                "powershell", "cmd", "paint", "task manager", "opentoonz",
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

    # Hardware — pin write
    hw_write = re.search(
        r"(?:turn|set|switch|put)\s+(?:pin\s+)?(\w+)\s+(on|off|high|low)"
        r"|(?:turn|switch)\s+(on|off)\s+(?:pin\s+)?(\w+)",
        c, re.IGNORECASE,
    )
    if hw_write:
        g = hw_write.groups()
        if g[0] and g[1]:   # "turn pin 13 on"
            pin   = g[0]
            state = "HIGH" if g[1].lower() in ("on", "high") else "LOW"
        else:               # "turn on pin 13"
            pin   = g[3] or ""
            state = "HIGH" if g[2] and g[2].lower() == "on" else "LOW"
        return ("hardware", {"action": "digital_write", "pin": pin, "value": state})

    # Hardware — temperature / DHT read
    if re.search(r"(read|get|what('s| is))\s+(temperature|temp|humidity|dht)", c, re.IGNORECASE):
        return ("hardware", {"action": "dht", "pin": "2"})

    # Hardware — analog read
    hw_aread = re.search(r"(?:read|get)\s+(?:analog\s+)?pin\s+(A?\d+)", c, re.IGNORECASE)
    if hw_aread:
        return ("hardware", {"action": "analog_read", "pin": hw_aread.group(1)})

    # Hardware — digital read
    hw_dread = re.search(r"(?:read|get)\s+(?:digital\s+)?pin\s+(\d+)", c, re.IGNORECASE)
    if hw_dread:
        return ("hardware", {"action": "digital_read", "pin": hw_dread.group(1)})

    # Hardware — list devices
    if re.search(r"(list|show|what)\s+(?:hardware\s+)?devices", c, re.IGNORECASE):
        return ("hardware", {"action": "list"})

    # Hardware — scan serial ports
    if re.search(r"scan\s+(?:for\s+)?(?:serial|com)\s+(?:port|device)", c, re.IGNORECASE):
        return ("hardware", {"action": "discover"})

    # Phone number dossier — natural language trigger
    # Matches: "profile +923001234567", "who is +1-555-867-5309", "dossier +447911123456"
    phone_intent = re.search(
        r"(?:profile|dossier|lookup|who\s+is|investigate|find\s+info|osint|intel(?:ligence)?)\s+"
        r"(\+?\d[\d\s\-().]{6,}\d)",
        content, re.IGNORECASE,
    )
    if not phone_intent:
        # Bare E.164 format anywhere in message
        phone_intent = re.search(r"(\+\d{1,3}[\d\s\-]{6,}\d)", content)
    if phone_intent:
        phone = re.sub(r"[\s\-()]", "", phone_intent.group(1))
        if len(re.sub(r"[^0-9]", "", phone)) >= 7:
            return ("phone_dossier", {"query": phone})

    return None

async def _handle_integration(client: "Client", msg_id: str, kind: str, params: dict) -> bool:
    """
    Handle a detected integration request directly.
    Returns True if handled, False if should fall through to LLM.
    """

    # ── All other integrations ────────────────────────────────────────────
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
        elif kind == "hardware":
            from hardware.registry       import list_all, load
            from hardware.command_router import handle_hardware_command
            load()
            devices   = list_all()
            device_id = devices[0].id if devices else ""
            action    = params.get("action", "list")
            hw_msg    = {"action": action, "device_id": device_id, **params}
            await handle_hardware_command(client, hw_msg)
            if device_id:
                ack = f"Hardware command dispatched — **{action}** on `{device_id}`. Results are visible in the Hardware panel."
            else:
                ack = f"Hardware command dispatched — **{action}**. Results are visible in the Hardware panel."
            await client.send({"type": "chat_chunk", "id": msg_id, "chunk": ack})
            await client.send({"type": "chat_done",  "id": msg_id, "provider": "hardware"})
            await client.send({"type": "visualizer", "mode": "speaking"})
            history = _histories.setdefault(client.id, [])
            history.append({"role": "assistant", "content": ack})
            return True
        elif kind == "phone_dossier":
            from intel.person import phone_full_dossier
            phone   = params.get("query", "")
            full_out = ""
            await client.send({"type": "visualizer", "mode": "listening"})
            async for chunk in phone_full_dossier(phone):
                full_out += chunk + "\n"
                await client.send({"type": "chat_chunk", "id": msg_id, "chunk": chunk + "\n"})
            await client.send({"type": "chat_done",  "id": msg_id, "provider": "intel"})
            await client.send({"type": "visualizer", "mode": "speaking"})
            history = _histories.setdefault(client.id, [])
            history.append({"role": "assistant", "content": full_out})
            return True
        else:
            return False

        # Stream result as chat chunks
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
    elif t == "hardware_command":        await _handle_hardware_command(client, msg)
    elif t == "hardware_confirm":        await _handle_hardware_confirm(client, msg)
    elif t == "offensive_action":        await _handle_offensive_action(client, msg)
    elif t == "offensive_confirm":       await _handle_offensive_confirm(client, msg)
    elif t == "vm_command":              await _handle_vm_command(client, msg)
    elif t == "tool_install":            await _handle_tool_install(client, msg)
    elif t == "vm_check_tools":          await _handle_vm_check_tools(client, msg)
    elif t == "device_action":           await _handle_device_action(client, msg)
    elif t == "device_confirm":          await _handle_device_confirm(client, msg)
    elif t == "adb_list":                await _handle_adb_list(client, msg)
    elif t == "screen_pair":             await _handle_screen_pair(client, msg)
    elif t == "screen_connect":          await _handle_screen_connect(client, msg)
    elif t == "screen_start":            await _handle_screen_start(client, msg)
    elif t == "screen_stop":             await _handle_screen_stop(client, msg)
    elif t == "screen_devices":          await _handle_screen_devices(client, msg)
    elif t == "guardian_action":         await _handle_guardian_action(client, msg)
    elif t == "lab_start":               await _handle_lab_start(client, msg)
    elif t == "lab_stop":                await _handle_lab_stop(client, msg)
    elif t == "lab_rat_action":          await _handle_lab_rat(client, msg)
    elif t == "lab_phish_stop":          await _handle_phish_stop(client, msg)
    elif t == "ops_session_create":      await _handle_ops_create(client, msg)
    elif t == "ops_target_add":          await _handle_ops_target_add(client, msg)
    elif t == "ops_target_remove":       await _handle_ops_target_remove(client, msg)
    elif t == "ops_session_list":        await _handle_ops_list(client, msg)
    elif t == "ops_session_close":       await _handle_ops_close(client, msg)
    elif t == "ops_auto_recon":          await _handle_ops_auto_recon(client, msg)
    elif t == "intel_action":            await _handle_intel_action(client, msg)
    elif t == "intel_confirm":           await _handle_intel_confirm(client, msg)
    elif t == "intel_graph_get":         await _handle_intel_graph_get(client, msg)
    elif t == "intel_graph_reset":       await _handle_intel_graph_reset(client, msg)
    elif t == "auto_start":              await _handle_auto_start(client, msg)
    elif t == "auto_stop":               await _handle_auto_stop(client, msg)
    elif t == "auto_confirm":            await _handle_auto_confirm(client, msg)
    elif t == "stealth_action":          await _handle_stealth_action(client, msg)
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
            # Filter out [ACTION: ...] blocks — they are machine instructions,
            # not meant for the user to see. Execute them silently.
            filtered = re.sub(r'\[ACTION:\s*[^\]]+\]', '', chunk).strip()
            if filtered:
                await client.send({"type": "chat_chunk", "id": msg_id, "chunk": filtered})

        history.append({"role": "assistant", "content": full_response})

        # Execute inline actions BEFORE sending chat_done so the user
        # sees the live execution output in the same chat bubble
        await _execute_inline_actions(client, msg_id, full_response)

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


async def _execute_inline_actions(client: "Client", msg_id: str, text: str) -> None:
    """Parse and execute [ACTION: ...] blocks generated by the LLM in standard chat."""
    from integrations.system_control import open_url, launch_app, _ps
    
    # 1. Open URLs
    for m in re.finditer(r'\[ACTION:\s*open_url\("([^"]+)"\)\]', text):
        url = m.group(1)
        log.info(f"inline action: open_url({url})")
        res = await open_url(url)
        await client.send({"type": "chat_chunk", "id": msg_id, "chunk": f"\n\n*[System: {res}]*"})

    # 2. Launch files / apps
    for m in re.finditer(r'\[ACTION:\s*launch_file\("([^"]+)"\)\]', text):
        path = m.group(1)
        log.info(f"inline action: launch_file({path})")
        res = await launch_app(path)
        if "[ERROR]" in res:
            # Fallback to Start-Process for generic files/videos
            res = await _ps(f'Start-Process "{path}"')
            if not res or res.startswith("[OK]"):
                res = f"Opened: {path}"
        await client.send({"type": "chat_chunk", "id": msg_id, "chunk": f"\n\n*[System: {res}]*"})

    # 3. OpenToonz actions — proper format: [ACTION: opentoonz_action("action_name")]
    for m in re.finditer(r'\[ACTION:\s*opentoonz_action\("([^"]+)"\)\]', text):
        action = m.group(1)
        log.info(f"inline action: opentoonz_action({action})")
        try:
            from integrations.opentoonz import execute as otoonz_exec
            res = await otoonz_exec(client, msg_id, action)
            await client.send({"type": "chat_chunk", "id": msg_id, "chunk": f"\n\n*[System: {res}]*"})
        except Exception as e:
            log.warning(f"opentoonz inline action error: {e}")
            await client.send({"type": "chat_chunk", "id": msg_id, "chunk": f"\n\n*[System: OpenToonz error — {e}]*"})

    # 4. Catch LLM-hallucinated send_keys — route through opentoonz bridge
    for m in re.finditer(r'\[ACTION:\s*send_keys\("([^"]+)"\)\]', text):
        keys = m.group(1)
        log.info(f"inline action: send_keys({keys}) → routing to opentoonz")
        try:
            from integrations.opentoonz import execute as otoonz_exec
            # Map common key combos to known actions
            key_map = {
                "Ctrl+N": "new_scene", "ctrl+n": "new_scene",
                "Ctrl+S": "save", "ctrl+s": "save",
                "Ctrl+Z": "undo", "ctrl+z": "undo",
                "Ctrl+Y": "redo", "ctrl+y": "redo",
                "Space": "play", "space": "play",
                "B": "brush", "b": "brush",
                "E": "eraser", "e": "eraser",
                "F": "fill", "f": "fill",
                "S": "select", "s": "select",
            }
            action = key_map.get(keys, keys.lower().replace("+", "_"))
            res = await otoonz_exec(client, msg_id, action)
            await client.send({"type": "chat_chunk", "id": msg_id, "chunk": f"\n\n*[System: {res}]*"})
        except Exception as e:
            log.warning(f"send_keys fallback error: {e}")

    # 5. Catch LLM-hallucinated send_mouse_draw — route to draw_stroke
    if re.search(r'\[ACTION:\s*send_mouse_draw\(', text):
        log.info("inline action: send_mouse_draw → routing to opentoonz draw_stroke")
        try:
            from integrations.opentoonz import execute as otoonz_exec
            res = await otoonz_exec(client, msg_id, "draw_stroke")
            await client.send({"type": "chat_chunk", "id": msg_id, "chunk": f"\n\n*[System: {res}]*"})
        except Exception as e:
            log.warning(f"send_mouse_draw fallback error: {e}")



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
    # Propagate VM connection settings whenever profile arrives
    vm_name  = data.get("vmName",    "")
    vm_ip    = data.get("vmIp",      "")
    ssh_user = data.get("vmSshUser", "")
    ssh_key  = data.get("vmSshKey",  "")
    ssh_pass = data.get("vmSshPass", "")
    if vm_ip and ssh_user and (ssh_key or ssh_pass):
        try:
            from offensive.vm_bridge import vm
            vm.configure(vm_name, vm_ip, ssh_user, ssh_key, ssh_pass)
        except Exception as e:
            log.warning(f"VM config sync failed: {e}")
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


# ─── Hardware ─────────────────────────────────────────────────────────────────

async def _handle_hardware_command(client: "Client", msg: dict) -> None:
    from hardware.command_router import handle_hardware_command
    await handle_hardware_command(client, msg)


async def _handle_hardware_confirm(client: "Client", msg: dict) -> None:
    from hardware.command_router import handle_hardware_confirm
    await handle_hardware_confirm(client, msg)


# ─── Offensive ────────────────────────────────────────────────────────────────

async def _handle_offensive_action(client: "Client", msg: dict) -> None:
    from offensive.orchestrator import handle_offensive_action
    await handle_offensive_action(client, msg)


async def _handle_offensive_confirm(client: "Client", msg: dict) -> None:
    from offensive.orchestrator import handle_offensive_confirm
    await handle_offensive_confirm(client, msg)


async def _handle_vm_command(client: "Client", msg: dict) -> None:
    from offensive.orchestrator import handle_vm_command
    await handle_vm_command(client, msg)


async def _handle_tool_install(client: "Client", msg: dict) -> None:
    from offensive.orchestrator import handle_tool_install
    await handle_tool_install(client, msg)


async def _handle_vm_check_tools(client: "Client", msg: dict) -> None:
    from offensive.orchestrator import check_vm_tools
    tools = msg.get("tools", [])
    await check_vm_tools(client, tools)


# ─── Devices ──────────────────────────────────────────────────────────────────

async def _handle_device_action(client: "Client", msg: dict) -> None:
    from devices.orchestrator import handle_device_action
    await handle_device_action(client, msg)


async def _handle_device_confirm(client: "Client", msg: dict) -> None:
    from devices.orchestrator import handle_device_confirm
    await handle_device_confirm(client, msg)


async def _handle_adb_list(client: "Client", msg: dict) -> None:
    from devices.orchestrator import handle_adb_list
    await handle_adb_list(client, msg)


# ─── Lab ──────────────────────────────────────────────────────────────────────

async def _handle_lab_start(client: "Client", msg: dict) -> None:
    from lab.scenario import start_lab
    asyncio.create_task(start_lab(client, msg))


async def _handle_lab_stop(client: "Client", msg: dict) -> None:
    from lab.scenario import stop_lab
    await stop_lab(client)


async def _handle_lab_rat(client: "Client", msg: dict) -> None:
    from lab import rat
    action  = msg.get("action", "")
    session = msg.get("session", "1")
    params  = msg.get("params", {})

    dispatch = {
        "webcam_snap":      lambda: rat.webcam_snap(client, session, params.get("camera", 1)),
        "record_mic":       lambda: rat.record_mic(client, session, int(params.get("duration", 10))),
        "geolocate":        lambda: rat.geolocate(client, session),
        "dump_contacts":    lambda: rat.dump_contacts(client, session),
        "dump_sms":         lambda: rat.dump_sms(client, session),
        "dump_call_log":    lambda: rat.dump_call_log(client, session),
        "browse_files":     lambda: rat.browse_files(client, params.get("path", "/sdcard"), session),
        "download_file":    lambda: rat.download_file(client, params.get("path", ""), session),
        "exfil_all":        lambda: rat.exfil_all(client, session),
        "keylogger_dump":   lambda: rat.keylogger_dump(client, session),
        "shell":            lambda: rat.shell_cmd(client, params.get("command", "id"), session),
        "hashdump":         lambda: rat.hashdump(client, session),
        "migrate":          lambda: rat.migrate_process(client, int(params.get("pid", 0)), session),
    }

    fn = dispatch.get(action)
    if fn:
        await fn()
    else:
        await client.send({"type": "lab_rat_result", "error": f"Unknown RAT action: {action}"})


async def _handle_phish_stop(client: "Client", msg: dict) -> None:
    from lab.phishing import stop_phishing_server
    stop_phishing_server()
    await client.send({"type": "lab_step_update", "step": "phishing",
                       "status": "done", "message": "Phishing server stopped"})


# ─── Ops session (real-world targets) ─────────────────────────────────────────

async def _handle_ops_create(client: "Client", msg: dict) -> None:
    from offensive.target_session import create_session
    sess = create_session(msg.get("name", "Operation"), msg.get("notes", ""))
    await client.send({"type": "ops_session", "session": sess.to_dict()})


async def _handle_ops_target_add(client: "Client", msg: dict) -> None:
    from offensive.target_session import add_target_to_active, get_active
    t = add_target_to_active(
        msg.get("target_type", "ip"),
        msg.get("value", ""),
        msg.get("scope_notes", ""),
        msg.get("program_url", ""),
    )
    sess = get_active()
    await client.send({
        "type":    "ops_session",
        "session": sess.to_dict() if sess else {},
        "added":   t.id if t else None,
    })


async def _handle_ops_target_remove(client: "Client", msg: dict) -> None:
    from offensive.target_session import get_active
    sess = get_active()
    if sess:
        sess.remove_target(msg.get("target_id", ""))
        await client.send({"type": "ops_session", "session": sess.to_dict()})


async def _handle_ops_list(client: "Client", msg: dict) -> None:
    from offensive.target_session import list_sessions
    await client.send({"type": "ops_sessions", "sessions": list_sessions()})


async def _handle_ops_close(client: "Client", msg: dict) -> None:
    from offensive.target_session import close_session
    close_session(msg.get("session_id", ""))
    await client.send({"type": "ops_closed", "session_id": msg.get("session_id", "")})


async def _handle_ops_auto_recon(client: "Client", msg: dict) -> None:
    """
    Full automated recon on a target:
    nmap → subdomain enum → CVE match → screenshot → report.
    """
    from offensive.target_session import get_active, add_target_to_active
    from offensive.vm_bridge import vm

    target = msg.get("target", "")
    if not target:
        await client.send({"type": "ops_recon_error", "error": "No target specified"})
        return

    # Auto-add to active session if not present
    sess = get_active()
    if not sess:
        from offensive.target_session import create_session
        sess = create_session(f"Recon: {target}")
    if not sess.in_scope(target):
        add_target_to_active("domain" if "." in target and not target[0].isdigit() else "ip", target)

    await client.send({"type": "ops_recon_start", "target": target})

    steps = [
        ("Port scan",       f"nmap -sV -T4 --open -F {target} 2>/dev/null"),
        ("Service scripts", f"nmap -sC -p 80,443,22,21,8080,8443 {target} 2>/dev/null"),
        ("Subdomains",      f"subfinder -d {target} -silent 2>/dev/null | head -30"),
        ("CVE lookup",      f"searchsploit {target.split('.')[-2] if '.' in target else target} 2>/dev/null | head -20"),
        ("Web headers",     f"curl -sIL --connect-timeout 5 http://{target} 2>/dev/null | head -20"),
        ("Tech detect",     f"whatweb -a 2 {target} 2>/dev/null"),
        ("SSL cert",        f"echo | openssl s_client -connect {target}:443 2>/dev/null | openssl x509 -noout -text 2>/dev/null | grep -E 'Subject:|DNS:|Issuer:' | head -10"),
    ]

    for step_name, cmd in steps:
        await client.send({"type": "ops_recon_step", "step": step_name, "target": target})
        async for line in vm.run(cmd, timeout=45):
            await client.send({"type": "ops_recon_chunk", "step": step_name, "chunk": line, "target": target})
        sess.record(f"recon:{step_name}", target, "completed")

    await client.send({"type": "ops_recon_done", "target": target,
                       "session": sess.to_dict()})


# ─── Intel ────────────────────────────────────────────────────────────────────

async def _handle_intel_action(client: "Client", msg: dict) -> None:
    from intel.orchestrator import handle_intel_action
    await handle_intel_action(client, msg)


async def _handle_intel_confirm(client: "Client", msg: dict) -> None:
    from intel.orchestrator import handle_intel_confirm
    await handle_intel_confirm(client, msg)


async def _handle_intel_graph_get(client: "Client", msg: dict) -> None:
    from intel.orchestrator import handle_intel_graph_get
    await handle_intel_graph_get(client)


async def _handle_intel_graph_reset(client: "Client", msg: dict) -> None:
    from intel.orchestrator import handle_intel_graph_reset
    await handle_intel_graph_reset(client)


# ─── Autonomous (Phase 12) ─────────────────────────────────────────────────────

async def _handle_auto_start(client: "Client", msg: dict) -> None:
    from autonomous.executor import start_task
    await start_task(client, msg)


async def _handle_auto_stop(client: "Client", msg: dict) -> None:
    from autonomous.executor import stop_task
    await stop_task(client, msg)


async def _handle_auto_confirm(client: "Client", msg: dict) -> None:
    from autonomous.executor import confirm_step
    await confirm_step(client, msg)


# ─── Stealth & Evasion (Phase 13) ─────────────────────────────────────────────

async def _handle_stealth_action(client: "Client", msg: dict) -> None:
    from stealth.orchestrator import handle_stealth_action
    action = msg.get("action", "")
    params = {**msg, "_msg_id": msg.get("id", "stealth")}
    await handle_stealth_action(client, action, params)


# ─── Screen Mirror (Phase 16) ──────────────────────────────────────────────────

async def _handle_screen_pair(client: "Client", msg: dict) -> None:
    from devices.screen_mirror import pair_device
    ip        = msg.get("ip", "")
    pair_port = msg.get("pair_port", "")
    pair_code = msg.get("pair_code", "")
    if not all([ip, pair_port, pair_code]):
        await client.send({"type": "screen_error", "error": "ip, pair_port and pair_code required"})
        return
    async for line in pair_device(ip, pair_port, pair_code):
        await client.send({"type": "screen_log", "line": line})
    await client.send({"type": "screen_pair_done"})


async def _handle_screen_connect(client: "Client", msg: dict) -> None:
    from devices.screen_mirror import connect_wireless
    ip   = msg.get("ip", "")
    port = msg.get("port", "5555")
    if not ip:
        await client.send({"type": "screen_error", "error": "ip required"})
        return
    async for line in connect_wireless(ip, port):
        await client.send({"type": "screen_log", "line": line})
    await client.send({"type": "screen_connect_done", "serial": f"{ip}:{port}"})


async def _handle_screen_devices(client: "Client", msg: dict) -> None:
    from devices.screen_mirror import list_connected
    devices = await list_connected()
    await client.send({"type": "screen_devices", "devices": devices})


async def _handle_screen_start(client: "Client", msg: dict) -> None:
    from devices.screen_mirror import stream_screen
    serial     = msg.get("serial", "")
    session_id = msg.get("session_id", "default")
    fps        = int(msg.get("fps", 2))
    if not serial:
        await client.send({"type": "screen_error", "error": "serial required"})
        return
    import asyncio as _asyncio
    _asyncio.create_task(stream_screen(client, serial, session_id, fps))


async def _handle_screen_stop(client: "Client", msg: dict) -> None:
    from devices.screen_mirror import stop_stream
    session_id = msg.get("session_id", "default")
    await stop_stream(client, session_id)


# ─── Guardian (Defensive Tools) ───────────────────────────────────────────────

async def _handle_guardian_action(client: "Client", msg: dict) -> None:
    action = msg.get("action", "")
    p      = msg.get("params", {})

    if action == "breach_email":
        from guardian.breach_monitor import check_email_breach
        async for line in check_email_breach(p.get("email", "")):
            await client.send({"type": "guardian_output", "line": line})

    elif action == "breach_phone":
        from guardian.breach_monitor import check_phone_breach
        async for line in check_phone_breach(p.get("phone", "")):
            await client.send({"type": "guardian_output", "line": line})

    elif action == "breach_domain":
        from guardian.breach_monitor import check_domain_breach
        async for line in check_domain_breach(p.get("domain", "")):
            await client.send({"type": "guardian_output", "line": line})

    elif action == "scan_network":
        from guardian.network_guardian import scan_network
        async for line in scan_network(p.get("network", "")):
            await client.send({"type": "guardian_output", "line": line})

    elif action == "check_router":
        from guardian.network_guardian import check_router_security
        async for line in check_router_security(p.get("router_ip", "192.168.1.1")):
            await client.send({"type": "guardian_output", "line": line})

    elif action == "check_link":
        from guardian.network_guardian import check_link_safety
        async for line in check_link_safety(p.get("url", "")):
            await client.send({"type": "guardian_output", "line": line})

    elif action == "harden_advice":
        from guardian.network_guardian import harden_device_advice
        async for line in harden_device_advice(p.get("os", "windows")):
            await client.send({"type": "guardian_output", "line": line})

    elif action == "investigate_attacker":
        from guardian.attack_detector import investigate_attacker
        async for line in investigate_attacker(p.get("ip", "")):
            await client.send({"type": "guardian_output", "line": line})

    elif action == "block_ip":
        from guardian.attack_detector import block_ip_local
        async for line in block_ip_local(p.get("ip", "")):
            await client.send({"type": "guardian_output", "line": line})

    elif action == "monitor_start":
        from guardian.attack_detector import monitor_connections
        session_id = p.get("session_id", "guardian_default")
        import asyncio as _asyncio
        _asyncio.create_task(monitor_connections(client, session_id))

    elif action == "monitor_stop":
        from guardian.attack_detector import stop_monitor
        await stop_monitor(client, p.get("session_id", "guardian_default"))

    await client.send({"type": "guardian_done", "action": action})
