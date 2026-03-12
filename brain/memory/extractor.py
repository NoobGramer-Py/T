import json
import httpx
import os
from core.logger import get_logger

log = get_logger("memory.extractor")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OLLAMA_URL   = "http://localhost:11434"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

_EXTRACT_PROMPT = """\
You are a memory extraction system for a personal AI assistant called T.

Analyze the following conversation exchange and extract any facts worth remembering long-term about the user or their context. These are facts that would be useful in future unrelated conversations.

Rules:
- Only extract concrete, specific facts (names, preferences, tools, goals, projects, systems, habits).
- Do NOT extract transient info (current questions, weather queries, one-off tasks).
- Do NOT extract things T said — only facts about the user or their environment.
- Return a JSON array. Each item: {"key": "short_snake_case_id", "value": "concise fact statement"}
- If nothing is worth remembering, return an empty array: []
- Maximum 5 facts per exchange.
- Keys must be unique identifiers like: user_os, preferred_language, project_name, target_ip, etc.

Exchange:
USER: {user_msg}
T: {assistant_msg}

Return ONLY the JSON array, no explanation."""


async def extract(
    user_msg:      str,
    assistant_msg: str,
    groq_key:      str = "",
) -> list[dict]:
    """
    Extract memorable facts from one exchange.
    Returns list of {"key": str, "value": str}.
    """
    prompt = _EXTRACT_PROMPT.format(
        user_msg=user_msg[:800],
        assistant_msg=assistant_msg[:800],
    )

    raw = ""
    try:
        if groq_key:
            raw = await _call_groq(prompt, groq_key)
        else:
            raw = await _call_ollama(prompt)
    except Exception as e:
        log.warning(f"extractor LLM call failed: {e}")
        return []

    return _parse(raw)


def _parse(raw: str) -> list[dict]:
    raw = raw.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return [
            {"key": str(item["key"]), "value": str(item["value"])}
            for item in data
            if isinstance(item, dict) and "key" in item and "value" in item
        ]
    except Exception:
        log.warning(f"extractor parse failed: {raw[:120]}")
        return []


async def _call_groq(prompt: str, api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       GROQ_MODEL,
        "messages":    [{"role": "user", "content": prompt}],
        "max_tokens":  256,
        "temperature": 0.0,
        "stream":      False,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(GROQ_API_URL, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def _call_ollama(prompt: str) -> str:
    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
        r.raise_for_status()
        return r.json()["response"]
