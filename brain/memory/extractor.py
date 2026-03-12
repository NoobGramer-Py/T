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
Extract memorable long-term facts about the user from this conversation exchange.

Rules:
- Only extract concrete facts: names, tools, preferences, projects, systems, targets, habits.
- Skip transient info: one-off questions, weather, current tasks that won't recur.
- Skip anything T said — only facts about the user or their environment.
- Maximum 5 facts.
- Return a JSON array only. No explanation, no markdown, no preamble.

Each item format: {{"key": "snake_case_id", "value": "fact about the user"}}

If nothing is worth remembering, return: []

USER: {user_msg}
T: {assistant_msg}

JSON array:"""


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
        inner = []
        for line in lines[1:]:
            if line.strip() == "```":
                break
            inner.append(line)
        raw = "\n".join(inner).strip()

    # If the model just echoed a fragment like "key" or empty — bail early
    if not raw or raw in ('"key"', "key", "[]", '""'):
        return []

    # Must start with [ to be a valid array
    if not raw.startswith("["):
        # Try to find an array inside the response
        start = raw.find("[")
        end   = raw.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []
        raw = raw[start:end + 1]

    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        results = []
        for item in data:
            if not isinstance(item, dict):
                continue
            key   = item.get("key",   "")
            value = item.get("value", "")
            # Skip malformed or placeholder entries
            if (
                not key or not value
                or key   in ("key",   "<key>",   "short_snake_case_id")
                or value in ("value", "<value>", "concise fact statement")
                or len(key) > 80
                or len(value) > 400
            ):
                continue
            results.append({"key": str(key), "value": str(value)})
        return results
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
