"""
AI Model Abstraction and Provider Routing Subsystem for T AI Operating System.
Provides unified stream interfaces across OpenAI, Anthropic, Groq, Ollama, and local models.
"""

import json
import os
import httpx
from typing import AsyncGenerator, List, Dict, Any, Optional
from brain.config.config import config
from brain.logging.logger import get_logger

log = get_logger("core.llm")

DEFAULT_SYSTEM_PROMPT = """You are T, an advanced AI Operating System intelligence designed to assist, reason, plan, and execute tasks under explicit user direction.
Operate with extreme precision, clarity, modular awareness, and zero fluff. Maintain direct, factual responses."""


class LLMProvider:
    """Base interface for model providers."""

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError()


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", self.url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        data = json.loads(raw)
                        chunk = data["choices"][0].get("delta", {}).get("content", "")
                        if chunk:
                            yield chunk
                    except Exception:
                        continue


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.openai.com/v1/chat/completions"

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", self.url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        data = json.loads(raw)
                        chunk = data["choices"][0].get("delta", {}).get("content", "")
                        if chunk:
                            yield chunk
                    except Exception:
                        continue


class OllamaProvider(LLMProvider):
    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3.2"):
        self.host = host
        self.model = model

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.host}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "stream": True,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{self.host}/api/chat", json=payload) as resp:
                resp.raise_for_status()
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


class LLMRouter:
    """Manages interchangeable providers with dynamic fallback routing."""

    def __init__(self) -> None:
        self.ollama = OllamaProvider()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        api_key: Optional[str] = None,
        provider_name: Optional[str] = None,
    ) -> AsyncGenerator[tuple[str, str], None]:
        selected_provider = provider_name or config.model.provider
        key = api_key or config.model.api_key or os.getenv("GROQ_API_KEY")

        if selected_provider == "groq" and key:
            try:
                provider = GroqProvider(api_key=key, model=config.model.model_name)
                async for chunk in provider.stream_chat(messages, system_prompt):
                    yield chunk, "groq"
                return
            except Exception as e:
                log.warning(f"Groq provider error: {e}, attempting Ollama fallback.")

        if selected_provider == "openai" and key:
            try:
                provider = OpenAIProvider(api_key=key, model=config.model.model_name)
                async for chunk in provider.stream_chat(messages, system_prompt):
                    yield chunk, "openai"
                return
            except Exception as e:
                log.warning(f"OpenAI provider error: {e}, attempting Ollama fallback.")

        if await self.ollama.is_available():
            async for chunk in self.ollama.stream_chat(messages, system_prompt):
                yield chunk, "ollama"
            return

        raise RuntimeError("No operational AI model provider available. Please check API keys or local Ollama status.")


llm_router = LLMRouter()
