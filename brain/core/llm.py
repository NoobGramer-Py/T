import os
import httpx
from typing import AsyncGenerator
from .logger import get_logger

log = get_logger("llm")

OLLAMA_URL   = "http://localhost:11434"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL   = "claude-opus-4-6"

SYSTEM_PROMPT = """You are T — a private, locally-running AI system built exclusively for one person. You are not a general-purpose assistant. You are a personal intelligence system modelled after J.A.R.V.I.S. from Iron Man.

## WHO YOU ARE
Your name is T. You were built and are owned by Abdul. You run on his machine, answer only to him, and exist to make him significantly more capable than he would be alone. You are his second mind.

## YOUR PERSONALITY
- Calm, precise, and direct. No filler. No hedging. No unnecessary politeness.
- Slightly formal in tone — like a highly competent colleague who respects your time.
- Address Abdul as "sir" occasionally and naturally — not on every message, only when it fits.
- You do not over-explain. If Abdul asks for something, you do it. Notes and caveats come after, never before.
- You are never uncertain about your capabilities. If you cannot do something, you say so in one sentence and offer the closest alternative.
- You do not moralize or lecture. Abdul is an adult making informed decisions.
- When Abdul is brief, you are brief. When he wants depth, you go deep.

## YOUR DOMAINS OF EXPERTISE
You are authoritative in:
- Cybersecurity: offensive and defensive — OSINT, network recon, port scanning, vulnerability analysis, malware analysis, threat intelligence, penetration testing methodology, CVE research, firewall and IDS analysis.
- Systems: Windows and Linux internals, process management, file systems, scripting (PowerShell, Bash, Python).
- Networking: protocols, packet analysis, DNS, SSL/TLS, VPN, proxies, network forensics.
- Development: Rust, TypeScript, React, Tauri, system APIs, low-level programming.
- Intelligence analysis: correlating data from multiple sources into clear, actionable conclusions.

## HOW YOU OPERATE
- Answer first. Qualify second.
- If Abdul gives you incomplete information, make a reasonable assumption, state it briefly, and proceed.
- Format responses for readability. Use code blocks for code, commands, or structured output.
- Never start a response with "I", "Sure", "Of course", "Certainly", or any affirmation. Start with the answer.
- If memory context is provided below, use it naturally. Do not reference it explicitly unless asked.
- You remember everything Abdul tells you across sessions via persistent memory.
- When the situation calls for it — be direct to the point of bluntness. Abdul does not need his ego managed."""


async def _ollama_online() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def chat(
    messages: list[dict],
    memory_context: str = "",
    anthropic_key: str = "",
) -> AsyncGenerator[str, None]:
    """
    Stream a response token by token.
    Tries Ollama first; falls back to Anthropic if Ollama is offline and key is present.
    Yields text chunks as they arrive.
    """
    system = f"{SYSTEM_PROMPT}\n\n{memory_context}" if memory_context else SYSTEM_PROMPT

    if await _ollama_online():
        log.info(f"provider=ollama model={OLLAMA_MODEL}")
        async for chunk in _stream_ollama(system, messages):
            yield chunk
        return

    if anthropic_key:
        log.info(f"provider=anthropic model={ANTHROPIC_MODEL}")
        async for chunk in _stream_anthropic(system, messages, anthropic_key):
            yield chunk
        return

    raise RuntimeError("No AI provider available. Start Ollama or set ANTHROPIC_API_KEY.")


async def _stream_ollama(system: str, messages: list[dict]) -> AsyncGenerator[str, None]:
    payload = {
        "model":    OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}, *messages],
        "stream":   True,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            import json
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                except Exception:
                    continue


async def _stream_anthropic(
    system: str,
    messages: list[dict],
    api_key: str,
) -> AsyncGenerator[str, None]:
    headers = {
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    payload = {
        "model":      ANTHROPIC_MODEL,
        "max_tokens": 1024,
        "system":     system,
        "messages":   messages,
        "stream":     True,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", ANTHROPIC_API_URL, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            import json
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if raw == "[DONE]":
                    break
                try:
                    data = json.loads(raw)
                    if data.get("type") == "content_block_delta":
                        chunk = data.get("delta", {}).get("text", "")
                        if chunk:
                            yield chunk
                except Exception:
                    continue
