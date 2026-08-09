"""
Intelligent Model Router & Automatic Failover Subsystem for T AI Operating System.
Orchestrates task classification, candidate selection, provider priorities, quota fallback, and stream execution.
"""

import asyncio
from typing import AsyncGenerator, List, Dict, Any, Optional, Tuple
from brain.config.config import config
from brain.core.providers.base import (
    AIProvider,
    AIRequest,
    ModelMetadata,
    RateLimitError,
    QuotaExceededError,
    AuthenticationError,
    ServiceUnavailableError,
    ModelUnavailableError,
    ProviderError,
    DEFAULT_SYSTEM_PROMPT,
)
from brain.core.model_registry import model_registry
from brain.core.task_classifier import task_classifier, TaskClassification
from brain.core.provider_health import health_tracker
from brain.core.providers.grok import GrokProvider
from brain.core.providers.gemini import GeminiProvider
from brain.core.providers.groq import GroqProvider
from brain.core.providers.cerebras import CerebrasProvider
from brain.core.providers.openrouter import OpenRouterProvider
from brain.core.providers.github import GitHubModelsProvider
from brain.core.providers.ollama import OllamaProvider
from brain.logging.logger import get_logger

log = get_logger("core.model_router")


class ModelRouter:
    """Central intelligent model router and failover orchestrator for T."""

    DEFAULT_PRIORITY_ORDER = ["grok", "gemini", "groq", "cerebras", "openrouter", "github", "ollama"]

    def __init__(self) -> None:
        self.ollama = OllamaProvider()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize provider subsystem, register models, discover local Ollama models."""
        if self._initialized:
            return

        log.info("Initializing Multi-Model Engine & Router...")

        # Register providers
        providers: List[AIProvider] = [
            GrokProvider(api_key=config.model.xai_api_key),
            GeminiProvider(api_key=config.model.gemini_api_key),
            GroqProvider(api_key=config.model.groq_api_key),
            CerebrasProvider(api_key=config.model.cerebras_api_key),
            OpenRouterProvider(api_key=config.model.openrouter_api_key),
            GitHubModelsProvider(api_key=config.model.github_api_key),
            self.ollama,
        ]

        for p in providers:
            model_registry.register_provider(p)
            # Initialize health status
            available = await p.is_available()
            status = "ok" if available else ("not_configured" if p.provider_id != "ollama" else "unavailable")
            health = health_tracker.get_or_create(p.provider_id)
            health.quota_status = status

            # Register models from provider
            try:
                models = await p.get_models()
                for m in models:
                    model_registry.register_model(m)
            except Exception as e:
                log.warning(f"Could not load models for provider {p.name}: {e}")

        # Check Ollama startup & discovery
        await self.ollama.ensure_service_running()
        local_models = await self.ollama.get_models()
        for lm in local_models:
            model_registry.register_model(lm)

        health_tracker.set_missing_models("ollama", self.ollama.missing_configured_models)

        self._initialized = True
        log.info("Multi-Model Engine & Router initialized successfully.")

    def get_candidate_models(
        self,
        classification: TaskClassification,
        provider_override: Optional[str] = None,
    ) -> List[Tuple[AIProvider, ModelMetadata]]:
        """
        Select and rank candidate models based on task classification, provider health,
        priority configuration, and local-first preference.
        """
        candidates: List[Tuple[AIProvider, ModelMetadata]] = []
        all_models = model_registry.get_all_models()
        configured_priorities = config.model.fallback_order or self.DEFAULT_PRIORITY_ORDER

        # Build priority map
        priority_map = {pid: idx for idx, pid in enumerate(configured_priorities)}

        for m in all_models:
            if not m.enabled:
                continue

            provider = model_registry.get_provider(m.provider)
            if not provider:
                continue

            # Check provider health & cooldown
            if not health_tracker.is_healthy(m.provider):
                continue

            # If provider override specified by user, restrict to that provider
            if provider_override and m.provider != provider_override:
                continue

            # Check privacy local requirement
            if classification.privacy == "local_only" and not m.local:
                continue

            candidates.append((provider, m))

        def score_candidate(item: Tuple[AIProvider, ModelMetadata]) -> float:
            prov, meta = item
            base_score = 100.0

            # Provider priority score
            p_idx = priority_map.get(prov.provider_id, 99)
            base_score -= p_idx * 10.0

            # Local preference adjustment
            if config.model.local_preferred:
                if meta.local:
                    base_score += 50.0
            else:
                if classification.privacy != "local_only" and meta.local:
                    base_score -= 30.0  # Prefer cloud if localPreferred is False

            # Task capability match score
            if classification.type == "coding" and "coding" in meta.capabilities:
                base_score += 25.0
            elif classification.type == "reasoning" and "reasoning" in meta.capabilities:
                base_score += 25.0
            elif classification.type == "fast_response" and "fast_response" in meta.capabilities:
                base_score += 20.0
            elif classification.type == "local" and meta.local:
                base_score += 30.0

            return base_score

        candidates.sort(key=score_candidate, reverse=True)
        return candidates

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        provider_name: Optional[str] = None,
    ) -> AsyncGenerator[Tuple[str, str, Optional[Dict[str, Any]]], None]:
        """
        Main chat interface for T Kernel.
        Classifies task, routes to optimal candidate model, and handles automatic failover.
        Yields (chunk_text, provider_id, metadata_event).
        """
        if not self._initialized:
            await self.initialize()

        # 1. Task Classification
        classification = task_classifier.classify(messages)
        log.info(f"[MODEL] Task classified: {classification.type}/{classification.complexity} (privacy={classification.privacy})")

        # 2. Build Candidate List
        candidates = self.get_candidate_models(classification, provider_override=provider_name)
        if not candidates:
            # Fallback check on all providers regardless of health to attempt recovery
            log.warning("[MODEL] No healthy candidate models found matching filters. Attempting emergency fallback.")
            for pid in self.DEFAULT_PRIORITY_ORDER:
                prov = model_registry.get_provider(pid)
                if prov and await prov.is_available():
                    models = await prov.get_models()
                    if models:
                        candidates.append((prov, models[0]))
                        break

        if not candidates:
            raise RuntimeError("No operational AI model provider available. Please check API keys or local Ollama status.")

        request = AIRequest(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            task_type=classification.type,
        )

        last_error: Optional[Exception] = None
        attempted_providers = []

        # 3. Failover Loop across candidates
        for provider, model_meta in candidates:
            pid = provider.provider_id
            mname = model_meta.model
            attempted_providers.append(pid)

            log.info(f"[MODEL] Selected provider: {provider.name} (model={mname})")
            log.info(f"[MODEL] Request started for provider {pid}")

            switch_notice = None
            if len(attempted_providers) > 1:
                switch_notice = {
                    "type": "model_switched",
                    "previous_provider": attempted_providers[-2],
                    "active_provider": pid,
                    "model": mname,
                    "reason": f"Automatic failover: previous provider unavailable ({type(last_error).__name__ if last_error else 'error'})",
                }
                log.info(f"[MODEL] Model switched to {pid}. Reason: previous provider failed.")

            chunks_received = 0
            try:
                async for chunk in provider.stream_chat(request, model_name=mname):
                    chunks_received += 1
                    yield chunk, pid, switch_notice
                    switch_notice = None  # Send switch notice only once with first chunk

                # If streaming succeeded cleanly
                log.info(f"[MODEL] Request successful with provider {pid} ({mname})")
                health_tracker.record_success(pid, mname)
                return

            except (RateLimitError, QuotaExceededError, AuthenticationError, ServiceUnavailableError, ModelUnavailableError, ProviderError) as e:
                last_error = e
                err_type = (
                    "rate_limit" if isinstance(e, RateLimitError) else
                    "quota_exceeded" if isinstance(e, QuotaExceededError) else
                    "auth_failed" if isinstance(e, AuthenticationError) else
                    "service_unavailable"
                )
                log.warning(f"[MODEL] Request failed for {pid}: {e}. Provider marked cooldown.")
                health_tracker.record_failure(pid, mname, err_type)

                if chunks_received > 0:
                    # If failure occurred mid-stream, inform stream before switching
                    log.warning(f"[MODEL] Partial stream failure from {pid} after {chunks_received} chunks. Attempting fallback.")

                # Short delay before trying next fallback candidate
                await asyncio.sleep(0.3)
                continue

            except Exception as e:
                last_error = e
                log.error(f"[MODEL] Unexpected error with provider {pid}: {e}", exc_info=True)
                health_tracker.record_failure(pid, mname, "unexpected")
                await asyncio.sleep(0.3)
                continue

        # If all candidates exhausted
        raise RuntimeError(f"All candidate AI providers failed. Last error: {last_error}")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        api_key: Optional[str] = None,
        provider_name: Optional[str] = None,
    ) -> AsyncGenerator[Tuple[str, str], None]:
        """Backward-compatible wrapper for existing kernel callers."""
        async for chunk, provider_id, _meta in self.stream_chat(
            messages=messages,
            system_prompt=system_prompt,
            provider_name=provider_name,
        ):
            yield chunk, provider_id


model_router = ModelRouter()
