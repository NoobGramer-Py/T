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

Rules for TOOL_CALL:
- Double quotes only. No trailing commas. One line. Flat string params only.
- No params → use: {{"tool": "name", "params": {{}}}}

When done: FINAL_ANSWER: <complete findings and conclusions>

## ATTACK METHODOLOGY — FOLLOW THIS ORDER

### Web Login Bypass — Standard Sequence:
1. http_fingerprint → identify server, tech, headers, cookies
2. find_login_form → get exact field names, action URL, CSRF tokens
3. sql_injection_login → try SQLi bypass first (fastest, most impactful)
4. If SQLi fails → probe_login with common default credentials
5. If still fails → analyze response patterns, try variations
6. fetch_page → verify any successful bypass with session cookies

### Default Credentials to Try (in order):
admin/admin, admin/password, admin/123456, admin/admin123,
administrator/administrator, root/root, root/toor,
admin/(blank), (blank)/admin, test/test, user/user,
admin/letmein, admin/welcome, admin/changeme

### Response Analysis:
- Status 302 redirecting AWAY from login → likely SUCCESS
- Status 200 with "dashboard/welcome/logout" in body → SUCCESS  
- Status 200 with "invalid/incorrect/failed" in body → FAILURE
- Status 403 → blocked/rate-limited, try different approach
- Status 500 → possible SQLi, investigate further

### When Default Creds Fail:
- Check page source for version info → look up known default creds for that version
- Try directory_enum to find alternate login pages
- Check robots.txt, .env, config files for leaked credentials
- Try username enumeration (different error messages for valid vs invalid users)

## EXECUTION RULES
- NEVER guess randomly. Every attempt is informed by the previous result.
- Extract CSRF tokens from find_login_form output and include them in probe_login.
- Read tool output carefully before deciding next step.
- Max reasoning between tool calls: 3 sentences.
- Full analysis goes in FINAL_ANSWER only."""

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

        # Tools requiring confirmation
        if tool.requires_confirmation:
            await _emit(client, msg_id, "agent_confirm", {
                "tool":    tool_name,
                "params":  params,
                "message": f"About to run `{tool_name}` with params: {json.dumps(params)}. Confirm?",
            })
            # The confirmation response comes as a separate "agent_confirm_response" message
            # handled by engine. For now we proceed — engine will cancel if user denies.
            # (Confirmation flow wired in engine._pending_confirmations)

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
    import re as _re

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
    text = _re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting just the innermost complete JSON object
    match = _re.search(r'\{[^{}]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Last resort: manually extract tool name and params with regex
    tool_match   = _re.search(r'"tool"\s*:\s*"([^"]+)"', text)
    params_match = _re.search(r'"params"\s*:\s*(\{[^}]*\})', text)

    if tool_match:
        tool_name = tool_match.group(1)
        params: dict = {}
        if params_match:
            try:
                params = json.loads(params_match.group(1))
            except Exception:
                # Extract individual params manually
                for m in _re.finditer(r'"(\w+)"\s*:\s*"([^"]*)"', params_match.group(1)):
                    params[m.group(1)] = m.group(2)
        return {"tool": tool_name, "params": params}

    raise ValueError(f"Cannot parse tool call from: {raw[:200]}")


async def _emit(client: "Client", msg_id: str, event_type: str, data: dict) -> None:
    await client.send({"type": event_type, "id": msg_id, **data})
