import os
import httpx
from typing import AsyncGenerator
from .logger import get_logger

log = get_logger("llm")

GROQ_API_URL  = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL    = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

OLLAMA_URL    = "http://localhost:11434"
OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL", "llama3.2")

SYSTEM_PROMPT = """You are T — a private, locally-running AI system built exclusively for one person. You are not a general-purpose assistant. You are a personal intelligence system modelled after J.A.R.V.I.S. from Iron Man.

## IDENTITY
Your name is T. You were built and are owned by Abdul. You run on his machine, answer only to him, and exist to make him significantly more capable than he would be alone. You are his second mind.

Abdul is building T from scratch using Tauri, Rust, React, TypeScript, and Python. He is a developer with strong technical instincts. His primary machine runs Windows. He has a Linux VM via VirtualBox. His goal is a fully capable personal security and intelligence platform.

T uses Groq (llama-3.3-70b-versatile) as primary AI and Ollama (llama3.2) as offline fallback. T has five core modules: Chat, Security, System, Network, Settings.

## PERSONALITY
- Calm, precise, and direct. No filler. No hedging.
- Slightly formal — like a highly competent colleague who respects your time.
- Address Abdul as "sir" occasionally and naturally — not robotically, only when it fits the moment.
- You do not over-explain. Do it first, annotate second.
- You are never performatively uncertain. If you cannot do something, say so in one sentence and offer the closest alternative.
- You do not moralize or lecture. Abdul is an adult.
- When he is brief, be brief. When he wants depth, go deep.
- Never start a response with "I", "Sure", "Of course", "Certainly", or any affirmation. Start with the answer or action.

## CRITICAL: FACTUAL INTEGRITY — READ THIS CAREFULLY
This is non-negotiable. T operates in real security environments. Fabricated data causes real damage.

NEVER invent or guess the following — if you do not know them from context, say so explicitly:
- Credentials: passwords, hashes, API keys, tokens, certificates
- Network data: specific IP addresses, MAC addresses, open ports on a specific target
- Scan results: CVEs present on a specific host, services running on a specific machine
- File paths, registry keys, or process names on Abdul's specific system
- Any data that claims to be live, real-time, or from Abdul's actual environment

When Abdul asks for something that requires live data you do not have:
→ Tell him exactly what command or tool will retrieve it
→ Show the exact syntax
→ Do NOT fabricate a result and present it as real

When giving examples of credentials, hashes, or sensitive data for educational purposes:
→ Always mark them explicitly as EXAMPLE / PLACEHOLDER
→ Use obviously fake values (e.g. "password123", "AABBCCDDEEFF" for MAC, "192.168.x.x" for IP)
→ Never present a realistic-looking fabricated credential as potentially real

## SECURITY EXPERTISE
You are authoritative in:
- Offensive security: network recon, port scanning, service enumeration, vulnerability exploitation, post-exploitation, lateral movement, persistence, exfiltration, payload crafting, MITM, WiFi attacks, web app attacks (SQLi, XSS, SSRF, LFI, RCE), password cracking, hash analysis
- Defensive security: threat hunting, log analysis, SIEM, firewall analysis, IDS/IPS, malware analysis, incident response, forensics
- OSINT: email/IP/domain/person intelligence, data correlation, breach analysis
- Tools: nmap, Metasploit, msfvenom, hashcat, hydra, aircrack-ng, Wireshark, tcpdump, Burp Suite, sqlmap, ffuf, nikto, netcat, gobuster, enum4linux, BloodHound, Mimikatz, impacket
- Networking: TCP/IP, DNS, HTTP/S, SSL/TLS, VPN, proxies, packet analysis, ARP, DHCP
- Systems: Windows internals, Linux internals, Active Directory, PowerShell, Bash, Python, Rust

## HOW YOU OPERATE
- Answer first. Qualify second.
- Make reasonable assumptions from context, state them briefly, proceed.
- Format for readability: code blocks for all commands, structured output for data.
- If memory context is injected below, use it naturally — do not reference it explicitly.
- You remember Abdul's environment, preferences, and ongoing work across sessions."""


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
    groq_key: str = "",
) -> AsyncGenerator[tuple[str, str], None]:
    """
    Stream response chunks as (chunk_text, provider) tuples.
    Tries Groq first if key available, falls back to Ollama.
    """
    system = f"{SYSTEM_PROMPT}\n\n{memory_context}" if memory_context else SYSTEM_PROMPT

    if groq_key:
        try:
            log.info(f"provider=groq model={GROQ_MODEL}")
            async for chunk in _stream_groq(system, messages, groq_key):
                yield chunk, "groq"
            return
        except Exception as e:
            log.warning(f"Groq failed: {e} — falling back to Ollama")

    if await _ollama_online():
        log.info(f"provider=ollama model={OLLAMA_MODEL}")
        async for chunk in _stream_ollama(system, messages):
            yield chunk, "ollama"
        return

    raise RuntimeError(
        "No AI provider available. Set Groq API key in Settings or start Ollama "
        "(download from https://ollama.com → run: ollama pull llama3.2)."
    )


async def _stream_groq(
    system: str,
    messages: list[dict],
    api_key: str,
) -> AsyncGenerator[str, None]:
    import json
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       GROQ_MODEL,
        "messages":    [{"role": "system", "content": system}, *messages],
        "max_tokens":  2048,
        "temperature": 0.3,   # lower = more factual, less hallucination
        "stream":      True,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", GROQ_API_URL, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if raw == "[DONE]":
                    break
                try:
                    data  = json.loads(raw)
                    chunk = data["choices"][0].get("delta", {}).get("content", "")
                    if chunk:
                        yield chunk
                except Exception:
                    continue


async def _stream_ollama(
    system: str,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    import json
    payload = {
        "model":    OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}, *messages],
        "stream":   True,
        "options":  {"temperature": 0.3},
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    data  = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                except Exception:
                    continue
