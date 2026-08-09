"""
Base provider abstraction and data models for T AI Operating System multi-model brain.
"""

import time
from dataclasses import dataclass, field
from typing import AsyncGenerator, List, Dict, Any, Optional

DEFAULT_SYSTEM_PROMPT = (
    "You are T, an advanced AI Operating System intelligence designed to assist, "
    "reason, plan, and execute tasks under explicit user direction. "
    "Operate with extreme precision, clarity, modular awareness, and zero fluff. "
    "Maintain direct, factual responses."
)


class ProviderError(Exception):
    """Base exception for provider errors."""
    pass


class RateLimitError(ProviderError):
    """Raised when provider returns rate limit status (HTTP 429)."""
    pass


class QuotaExceededError(ProviderError):
    """Raised when quota is depleted or account disabled (HTTP 402/403)."""
    pass


class AuthenticationError(ProviderError):
    """Raised when API key is invalid (HTTP 401)."""
    pass


class ServiceUnavailableError(ProviderError):
    """Raised when provider service is down or failing (HTTP 500/502/503/504)."""
    pass


class ModelUnavailableError(ProviderError):
    """Raised when requested model is unavailable or not found."""
    pass


@dataclass
class ModelMetadata:
    provider: str
    model: str
    capabilities: List[str] = field(default_factory=lambda: ["general_chat"])
    context_window: Optional[int] = 4096
    priority: int = 10
    enabled: bool = True
    local: bool = False


@dataclass
class ProviderHealth:
    provider: str
    model: str
    requests_today: int = 0
    failures: int = 0
    rate_limited: bool = False
    temporarily_unavailable: bool = False
    quota_status: str = "ok"  # "ok" | "rate_limited" | "quota_exceeded" | "unavailable" | "not_configured"
    last_successful_request: Optional[float] = None
    last_failure: Optional[float] = None
    cooldown_until: Optional[float] = None
    missing_models: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "requestsToday": self.requests_today,
            "failures": self.failures,
            "rateLimited": self.rate_limited,
            "temporarilyUnavailable": self.temporarily_unavailable,
            "quotaStatus": self.quota_status,
            "lastSuccessfulRequest": self.last_successful_request,
            "lastFailure": self.last_failure,
            "cooldownUntil": self.cooldown_until,
            "missingModels": self.missing_models,
        }


@dataclass
class AIRequest:
    messages: List[Dict[str, str]]
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    temperature: float = 0.7
    max_tokens: int = 4096
    task_type: str = "general"
    model_override: Optional[str] = None


class AIProvider:
    """Abstract base class for all AI model providers in T."""

    def __init__(self, provider_id: str, name: str) -> None:
        self.provider_id = provider_id
        self.name = name

    async def is_available(self) -> bool:
        """Check if provider credentials/endpoint are configured and valid."""
        raise NotImplementedError()

    async def get_models(self) -> List[ModelMetadata]:
        """Return list of models supported by this provider."""
        raise NotImplementedError()

    async def stream_chat(
        self,
        request: AIRequest,
        model_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks for the request."""
        raise NotImplementedError()

    @staticmethod
    def mask_key(key: Optional[str]) -> str:
        if not key:
            return ""
        if len(key) <= 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"
