"""
Agent executor for T.
Parses LLM tool-call decisions, executes tools, feeds results back,
streams all progress to the Tauri client in real time.
"""

import json
import re
from typing import TYPE_CHECKING
from core.logger import get_logger
from agents.tools import get_tool, tool_descriptions, TOOLS

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("agents.executor")

# Injected by engine at import time
_groq_key: str = ""

def set_groq_key(key: str) -> None:
    global _groq_key
    _groq_key = key


AGENT_SYSTEM = """You are T's execution agent — an autonomous security operator. You solve tasks by calling tools in sequence, thinking like a professional penetration tester.

## AVAILABLE TOOLS
{tools}

## RESPONSE FORMAT
When you need a tool, output EXACTLY this on one line:
TOOL_CALL: {{"tool": "tool_name", "params": {{"key": "value"}}}}

Rules: double quotes only, no trailing commas, one line, flat string params.
No params → {{"tool": "name", "params": {{}}}}

When finished: FINAL_ANSWER: <complete findings>

## CRITICAL — NO FABRICATION
You MUST read the actual tool output before drawing conclusions.
NEVER report success unless the tool output explicitly shows:
- A redirect to a location different from the login page, OR
- A new session/auth cookie in the response, OR
- Body content containing authenticated page elements (dashboard, logout link)

If tool output is ambiguous → report it as ambiguous. Do NOT assume success.
If all attacks fail → report failure honestly with what was tried.

## ATTACK METHODOLOGY

### WordPress Login (wp-login.php):
1. http_fingerprint → confirm WordPress version, plugins
2. wordpress_user_enum → find real usernames (critical — do not skip)
3. sql_injection_login → test SQLi (compare each result to BASELINE in output)
4. probe_login with confirmed usernames + common passwords
5. fetch_page with any obtained cookies to verify access

### WordPress Success Detection:
- Redirect to /wp-admin/ = SUCCESS (different from baseline /wp-login.php redirect)
- New wordpress_logged_in_* cookie in response = SUCCESS
- Redirect back to /wp-login.php?... = FAILURE
- Body contains "ERROR" or "incorrect" = FAILURE

### Generic Login:
1. http_fingerprint → identify tech stack
2. find_login_form → get exact field names + CSRF token
3. sql_injection_login → SQLi bypass (read DIFFERS_FROM_BASELINE field)
4. probe_login → default credentials with confirmed field names
5. directory_enum if login page is hardened

### Default Credentials (try in order):
admin/admin, admin/password, admin/123456, admin/admin123,
administrator/administrator, root/root, test/test, admin/(blank)

### Reading probe_login / sql_injection_login Output:
- Read the ACTUAL status code, redirect location, and cookies
- Compare redirect to what a failed login shows (baseline)
- Only claim bypass if redirect destination differs AND is not the login page
- Report the exact cookie name and value if auth cookies are found

## RULES
- Only call tools from the list — exact names
- Confirmation required tools: ask, then proceed when confirmed
- Never fabricate tool output
- Keep reasoning between tool calls to 2-3 sentences max
- Full analysis in FINAL_ANSWER only"""

MAX_STEPS = 20  # enough for a full attack chain


async def run_agent(
    client:  "Client",
    task:    str,
    profile: dict,
    msg_id:  str,
) -> str:
    """
    Run an agentic task loop:
    1. Ask LLM what to do next
    2. Parse tool call
    3. If confirmation required → ask client → wait for response
    4. Execute tool → feed result back to LLM
    5. Repeat until FINAL_ANSWER

    Returns the final answer string.
    Streams progress via agent_step events to the client.
    """

    groq_key = profile.get("groqKey", "") or _groq_key

    system = AGENT_SYSTEM.format(tools=tool_descriptions())
    messages: list[dict] = [{"role": "user", "content": task}]
    step = 0

    await _emit(client, msg_id, "agent_start", {"task": task})

    while step < MAX_STEPS:
        step += 1
        log.info(f"agent step {step}/{MAX_STEPS}")

        # Ask LLM what to do
        raw_response = ""
        async for chunk in _call_llm(system, messages, groq_key):
            raw_response += chunk

        messages.append({"role": "assistant", "content": raw_response})
        await _emit(client, msg_id, "agent_thought", {"text": raw_response, "step": step})

        # Check for FINAL_ANSWER
        if "FINAL_ANSWER:" in raw_response:
            answer = raw_response.split("FINAL_ANSWER:", 1)[1].strip()
            await _emit(client, msg_id, "agent_done", {"answer": answer})
            return answer

        # Check for TOOL_CALL — match from opening brace to last closing brace on the block
        tool_match = re.search(r'TOOL_CALL:\s*(\{.+?\})\s*$', raw_response, re.DOTALL | re.MULTILINE)
        if not tool_match:
            # Also try without line anchor in case it's mid-text
            tool_match = re.search(r'TOOL_CALL:\s*(\{.+?\})', raw_response, re.DOTALL)
        if not tool_match:
            # LLM responded without a tool call or final answer — treat as final
            await _emit(client, msg_id, "agent_done", {"answer": raw_response})
            return raw_response

        try:
            call      = _parse_tool_call(tool_match.group(1))
            tool_name = call.get("tool", "")
            params    = call.get("params", {})
        except Exception as e:
            err = f"[AGENT ERROR] Could not parse tool call: {e}\nRaw: {tool_match.group(1)[:200]}"
            log.warning(err)
            await _emit(client, msg_id, "agent_error", {"error": err})
            messages.append({"role": "user", "content": err + " Please output valid JSON."})
            continue

        tool = get_tool(tool_name)
        if not tool:
            err = f"[AGENT ERROR] Unknown tool: {tool_name!r}. Available: {', '.join(TOOLS)}"
            messages.append({"role": "user", "content": err})
            continue

        # Tools requiring confirmation — actually wait for the user's response
        if tool.requires_confirmation:
            confirmed = await _await_confirmation(client, msg_id, tool_name, params)
            if not confirmed:
                msg_denied = f"[USER DENIED] Tool '{tool_name}' was not confirmed. Do not retry this tool. Report what was attempted and move on."
                messages.append({"role": "user", "content": msg_denied})
                await _emit(client, msg_id, "agent_tool_denied", {"tool": tool_name})
                continue

        await _emit(client, msg_id, "agent_tool_start", {"tool": tool_name, "params": params})
        log.info(f"running tool  name={tool_name}  params={params}")

        try:
            result = await tool.fn(**params)
        except Exception as e:
            result = f"[TOOL ERROR] {e}"

        log.info(f"tool result  name={tool_name}  len={len(result)}")
        await _emit(client, msg_id, "agent_tool_done", {"tool": tool_name, "result": result})

        # Feed result back to LLM
        messages.append({"role": "user", "content": f"[TOOL RESULT: {tool_name}]\n{result}"})

    # Hit step limit
    final = "Task incomplete: maximum reasoning steps reached. Here is what was gathered so far."
    await _emit(client, msg_id, "agent_done", {"answer": final})
    return final


async def _call_llm(system: str, messages: list[dict], groq_key: str):
    """Stream LLM completion for the agent."""
    from core.llm import (
        _stream_groq, _ollama_online, _stream_ollama,
        GROQ_MODEL_SECURITY, OLLAMA_MODEL_DEFAULT,
    )
    if groq_key:
        async for chunk in _stream_groq(system, messages, groq_key, GROQ_MODEL_SECURITY):
            yield chunk
        return
    if await _ollama_online():
        async for chunk in _stream_ollama(system, messages, OLLAMA_MODEL_DEFAULT):
            yield chunk
        return
    raise RuntimeError("No LLM provider available for agent.")


def _parse_tool_call(raw: str) -> dict:
    """
    Parse a tool call JSON block from the LLM.
    Handles: trailing commas, single quotes, extra whitespace,
    unquoted keys, and other common LLM formatting mistakes.
    """
    text = raw.strip()

    # First try strict JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Replace single quotes with double quotes (common LLM mistake)
    text = text.replace("'", '"')
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting just the innermost complete JSON object
    match = re.search(r'\{[^{}]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Last resort: manually extract tool name and params with regex
    tool_match   = re.search(r'"tool"\s*:\s*"([^"]+)"', text)
    params_match = re.search(r'"params"\s*:\s*(\{[^}]*\})', text)

    if tool_match:
        tool_name = tool_match.group(1)
        params: dict = {}
        if params_match:
            try:
                params = json.loads(params_match.group(1))
            except Exception:
                # Extract individual params manually
                for m in re.finditer(r'"(\w+)"\s*:\s*"([^"]*)"', params_match.group(1)):
                    params[m.group(1)] = m.group(2)
        return {"tool": tool_name, "params": params}

    raise ValueError(f"Cannot parse tool call from: {raw[:200]}")


async def _await_confirmation(
    client: "Client", msg_id: str, tool_name: str, params: dict
) -> bool:
    """
    Send an agent_confirm event and block until the user responds
    (via agent_confirm_response message routed through engine._pending_confirms).
    Times out after 60 seconds and defaults to denied.
    """
    import core.engine as _engine  # lazy import — no circular dependency at runtime

    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    _engine._pending_confirms[client.id] = fut

    await _emit(client, msg_id, "agent_confirm", {
        "tool":    tool_name,
        "params":  params,
        "message": f"About to run `{tool_name}` — confirm?",
    })

    try:
        return await asyncio.wait_for(fut, timeout=60.0)
    except asyncio.TimeoutError:
        return False
    finally:
        _engine._pending_confirms.pop(client.id, None)


async def _emit(client: "Client", msg_id: str, event_type: str, data: dict) -> None:
    await client.send({"type": event_type, "id": msg_id, **data})
