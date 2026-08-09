"""
Google Gemini AI Provider for T AI Operating System.
"""

import json
import os
import httpx
from typing import AsyncGenerator, List, Optional
from brain.core.providers.base import (
    AIProvider,
    AIRequest,
    ModelMetadata,
    RateLimitError,
    QuotaExceededError,
    AuthenticationError,
    ServiceUnavailableError,
    ProviderError,
)
from brain.logging.logger import get_logger

log = get_logger("providers.gemini")


class GeminiProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions") -> None:
        super().__init__("gemini", "Google Gemini")
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.base_url = base_url

    async def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    async def get_models(self) -> List[ModelMetadata]:
        return [
            ModelMetadata(
                provider="gemini",
                model="gemini-2.5-flash",
                capabilities=["general_chat", "fast_response", "vision", "long_context", "coding"],
                context_window=1000000,
                priority=2,
                enabled=True,
                local=False,
            ),
            ModelMetadata(
                provider="gemini",
                model="gemini-2.5-pro",
                capabilities=["general_chat", "reasoning", "coding", "long_context", "vision"],
                context_window=2000000,
                priority=3,
                enabled=True,
                local=False,
            ),
            ModelMetadata(
                provider="gemini",
                model="gemini-1.5-flash",
                capabilities=["general_chat", "fast_response"],
                context_window=1000000,
                priority=4,
                enabled=True,
                local=False,
            ),
        ]

    async def stream_chat(
        self,
        request: AIRequest,
        model_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        if not await self.is_available():
            raise AuthenticationError("Gemini API key is not configured.")

        selected_model = model_name or request.model_override or "gemini-2.5-flash"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": selected_model,
            "messages": [{"role": "system", "content": request.system_prompt}, *request.messages],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", self.base_url, headers=headers, json=payload) as resp:
                    if resp.status_code == 401:
                        raise AuthenticationError(f"Gemini auth failed: {resp.status_code}")
                    elif resp.status_code == 429:
                        raise RateLimitError(f"Gemini rate limit reached: {resp.status_code}")
                    elif resp.status_code in (402, 403):
                        raise QuotaExceededError(f"Gemini quota exceeded: {resp.status_code}")
                    elif resp.status_code >= 500:
                        raise ServiceUnavailableError(f"Gemini service error: {resp.status_code}")
                    elif resp.status_code >= 400:
                        raise ProviderError(f"Gemini request failed with status {resp.status_code}")

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
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            raise ServiceUnavailableError(f"Gemini network timeout/failure: {e}")
