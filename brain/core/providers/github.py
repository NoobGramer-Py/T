"""
GitHub Models AI Provider for T AI Operating System.
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

log = get_logger("providers.github")


class GitHubModelsProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://models.inference.ai.azure.com/chat/completions") -> None:
        super().__init__("github", "GitHub Models")
        self.api_key = api_key or os.getenv("GITHUB_MODELS_API_KEY", os.getenv("GITHUB_TOKEN", ""))
        self.base_url = base_url

    async def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    async def get_models(self) -> List[ModelMetadata]:
        return [
            ModelMetadata(
                provider="github",
                model="gpt-4o",
                capabilities=["general_chat", "reasoning", "coding", "vision"],
                context_window=128000,
                priority=6,
                enabled=True,
                local=False,
            ),
            ModelMetadata(
                provider="github",
                model="gpt-4o-mini",
                capabilities=["general_chat", "fast_response", "coding"],
                context_window=128000,
                priority=6,
                enabled=True,
                local=False,
            ),
            ModelMetadata(
                provider="github",
                model="Phi-3-mini-4k-instruct",
                capabilities=["fast_response", "general_chat"],
                context_window=4096,
                priority=7,
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
            raise AuthenticationError("GitHub Models API key is not configured.")

        selected_model = model_name or request.model_override or "gpt-4o-mini"
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
                        raise AuthenticationError(f"GitHub Models auth failed: {resp.status_code}")
                    elif resp.status_code == 429:
                        raise RateLimitError(f"GitHub Models rate limit reached: {resp.status_code}")
                    elif resp.status_code in (402, 403):
                        raise QuotaExceededError(f"GitHub Models quota exceeded: {resp.status_code}")
                    elif resp.status_code >= 500:
                        raise ServiceUnavailableError(f"GitHub Models service error: {resp.status_code}")
                    elif resp.status_code >= 400:
                        raise ProviderError(f"GitHub Models request failed with status {resp.status_code}")

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
            raise ServiceUnavailableError(f"GitHub Models network timeout/failure: {e}")
