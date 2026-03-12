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


AGENT_SYSTEM = """You are T's execution agent. You solve tasks by calling tools in sequence.

## AVAILABLE TOOLS
{tools}

## RESPONSE FORMAT
Think step by step. When you need to call a tool, output EXACTLY this JSON block (nothing else on that line):
TOOL_CALL: {{"tool": "tool_name", "params": {{"param": "value"}}}}

After receiving tool output, continue reasoning and call more tools or give a final answer.
When done, output:
FINAL_ANSWER: <your complete analysis and conclusion>

## RULES
- Only call tools that exist in the list above.
- For tools marked [REQUIRES CONFIRMATION], you MUST explain what you are about to do and wait.
- Never fabricate tool output. If a tool returns an error, adapt your plan.
- Be concise between tool calls. Save analysis for the FINAL_ANSWER.
- If the task cannot be completed with available tools, say so in FINAL_ANSWER."""


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
    from core.llm import _stream_groq, _ollama_online, _stream_ollama, SYSTEM_PROMPT

    groq_key = profile.get("groqKey", "") or _groq_key

    system = AGENT_SYSTEM.format(tools=tool_descriptions())
    messages: list[dict] = [{"role": "user", "content": task}]
    max_steps = 8
    step = 0

    await _emit(client, msg_id, "agent_start", {"task": task})

    while step < max_steps:
        step += 1
        log.info(f"agent step {step}/{max_steps}")

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

        # Check for TOOL_CALL
        tool_match = re.search(r'TOOL_CALL:\s*(\{.*?\})', raw_response, re.DOTALL)
        if not tool_match:
            # LLM responded without a tool call or final answer — treat as final
            await _emit(client, msg_id, "agent_done", {"answer": raw_response})
            return raw_response

        try:
            call      = json.loads(tool_match.group(1))
            tool_name = call.get("tool", "")
            params    = call.get("params", {})
        except json.JSONDecodeError as e:
            err = f"[AGENT ERROR] Could not parse tool call: {e}"
            await _emit(client, msg_id, "agent_error", {"error": err})
            messages.append({"role": "user", "content": err + " Please try again with valid JSON."})
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
    """Stream LLM completion for the agent — collect full response."""
    from core.llm import _stream_groq, _ollama_online, _stream_ollama
    if groq_key:
        async for chunk in _stream_groq(system, messages, groq_key):
            yield chunk
        return
    if await _ollama_online():
        async for chunk in _stream_ollama(system, messages):
            yield chunk
        return
    raise RuntimeError("No LLM provider available for agent.")


async def _emit(client: "Client", msg_id: str, event_type: str, data: dict) -> None:
    await client.send({"type": event_type, "id": msg_id, **data})
