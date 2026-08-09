"""
Ollama Local AI Provider and Process Lifecycle Manager for T AI Operating System.
"""

import asyncio
import json
import os
import shutil
import subprocess
import httpx
from typing import AsyncGenerator, List, Optional, Dict, Any
from brain.core.providers.base import (
    AIProvider,
    AIRequest,
    ModelMetadata,
    ServiceUnavailableError,
    ModelUnavailableError,
    ProviderError,
)
from brain.logging.logger import get_logger

log = get_logger("providers.ollama")


class OllamaProvider(AIProvider):
    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: str = "llama3.2",
        reasoning_model: str = "qwen3:30b",
    ) -> None:
        super().__init__("ollama", "Ollama Local")
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.default_model = default_model
        self.reasoning_model = reasoning_model
        self.discovered_models: List[str] = []
        self.missing_configured_models: List[str] = []
        self._process: Optional[subprocess.Popen] = None

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def ensure_service_running(self) -> bool:
        """Attempt to check/start Ollama local service using OS mechanism if not reachable."""
        if await self.is_available():
            log.info("Ollama service is reachable.")
            await self.refresh_installed_models()
            return True

        log.info("Ollama service not responding. Attempting background startup...")
        ollama_bin = shutil.which("ollama") or shutil.which("ollama.exe")
        if ollama_bin:
            try:
                # Spawn non-blocking background process
                self._process = subprocess.Popen(
                    [ollama_bin, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                # Wait up to 3 seconds for service startup
                for _ in range(6):
                    await asyncio.sleep(0.5)
                    if await self.is_available():
                        log.info("Ollama service successfully started.")
                        await self.refresh_installed_models()
                        return True
            except Exception as e:
                log.warning(f"Failed to spawn Ollama process: {e}")

        log.warning("Ollama service unavailable. T will operate with cloud providers.")
        return False

    async def refresh_installed_models(self) -> List[str]:
        """Query Ollama API to discover installed local models."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                    self.discovered_models = models
                    self._check_missing_models()
                    return models
        except Exception as e:
            log.debug(f"Error fetching Ollama models: {e}")
        self.discovered_models = []
        return []

    def _check_missing_models(self) -> None:
        missing = []
        configured = [self.default_model, self.reasoning_model]
        for cfg_model in configured:
            if not cfg_model:
                continue
            # Match exact or base tag
            found = any(m == cfg_model or m.startswith(f"{cfg_model}:") or cfg_model.startswith(f"{m}:") for m in self.discovered_models)
            if not found:
                missing.append(cfg_model)
        self.missing_configured_models = missing
        if missing:
            log.warning(f"Ollama configured local models missing: {', '.join(missing)}")

    async def get_models(self) -> List[ModelMetadata]:
        result: List[ModelMetadata] = []
        if not self.discovered_models:
            await self.refresh_installed_models()

        for idx, model_name in enumerate(self.discovered_models):
            caps = ["general_chat", "local"]
            if "coder" in model_name or "code" in model_name:
                caps.append("coding")
            if "r1" in model_name or "reasoning" in model_name or "qwen3" in model_name:
                caps.append("reasoning")
            if "vision" in model_name or "llava" in model_name:
                caps.append("vision")

            result.append(
                ModelMetadata(
                    provider="ollama",
                    model=model_name,
                    capabilities=caps,
                    context_window=16384,
                    priority=7 + idx,
                    enabled=True,
                    local=True,
                )
            )

        # Include default fallback entry if no models yet discovered
        if not result:
            result.append(
                ModelMetadata(
                    provider="ollama",
                    model=self.default_model,
                    capabilities=["general_chat", "local"],
                    context_window=8192,
                    priority=7,
                    enabled=True,
                    local=True,
                )
            )
        return result

    async def stream_chat(
        self,
        request: AIRequest,
        model_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        if not await self.is_available():
            raise ServiceUnavailableError("Ollama local service is not reachable.")

        selected_model = model_name or request.model_override or (
            self.discovered_models[0] if self.discovered_models else self.default_model
        )

        payload = {
            "model": selected_model,
            "messages": [{"role": "system", "content": request.system_prompt}, *request.messages],
            "stream": True,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                    if resp.status_code == 404:
                        raise ModelUnavailableError(f"Ollama model '{selected_model}' is not installed.")
                    elif resp.status_code >= 400:
                        raise ProviderError(f"Ollama error status {resp.status_code}")

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
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            raise ServiceUnavailableError(f"Ollama network error: {e}")
