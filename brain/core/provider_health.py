"""
Provider Health & Quota Tracking System for T AI Operating System.
Tracks rate limits, failures, cooldown periods, and operational readiness for all AI providers.
"""

import time
from typing import Dict, Any, List, Optional
from brain.core.providers.base import ProviderHealth
from brain.logging.logger import get_logger

log = get_logger("core.provider_health")


class ProviderHealthTracker:
    """Manages system health state, quota/rate-limit tracking, and cooldown cycles for providers."""

    def __init__(self, default_cooldown_seconds: float = 60.0) -> None:
        self.default_cooldown_seconds = default_cooldown_seconds
        self.health_map: Dict[str, ProviderHealth] = {}

    def get_or_create(self, provider_id: str, default_model: str = "") -> ProviderHealth:
        if provider_id not in self.health_map:
            self.health_map[provider_id] = ProviderHealth(
                provider=provider_id,
                model=default_model,
                quota_status="ok",
            )
        return self.health_map[provider_id]

    def is_healthy(self, provider_id: str) -> bool:
        """Return True if provider is operational and not currently cooling down."""
        health = self.health_map.get(provider_id)
        if not health:
            return True

        # Check cooldown expiration
        if health.cooldown_until:
            now = time.time()
            if now >= health.cooldown_until:
                # Cooldown expired -> auto re-enable
                log.info(f"[HEALTH] Provider {provider_id} cooldown period expired. Re-enabling.")
                health.cooldown_until = None
                health.rate_limited = False
                health.temporarily_unavailable = False
                health.quota_status = "ok"
                return True
            else:
                return False

        return not (health.rate_limited or health.temporarily_unavailable)

    def record_success(self, provider_id: str, model_name: str) -> None:
        health = self.get_or_create(provider_id, model_name)
        health.model = model_name
        health.requests_today += 1
        health.last_successful_request = time.time()
        health.rate_limited = False
        health.temporarily_unavailable = False
        health.quota_status = "ok"
        health.cooldown_until = None

    def record_failure(
        self,
        provider_id: str,
        model_name: str,
        error_type: str,
        cooldown_seconds: Optional[float] = None,
    ) -> None:
        health = self.get_or_create(provider_id, model_name)
        health.model = model_name
        health.failures += 1
        health.last_failure = time.time()

        cd = cooldown_seconds or self.default_cooldown_seconds
        health.cooldown_until = time.time() + cd

        if error_type == "rate_limit":
            health.rate_limited = True
            health.temporarily_unavailable = True
            health.quota_status = "rate_limited"
            log.warning(f"[HEALTH] Provider {provider_id} rate limited. Cooldown for {cd:.0f}s.")

        elif error_type == "quota_exceeded":
            health.temporarily_unavailable = True
            health.quota_status = "quota_exceeded"
            log.warning(f"[HEALTH] Provider {provider_id} quota exceeded. Cooldown for {cd:.0f}s.")

        elif error_type == "auth_failed":
            health.temporarily_unavailable = True
            health.quota_status = "not_configured"
            log.warning(f"[HEALTH] Provider {provider_id} auth failed. Marked unconfigured.")

        else:
            health.temporarily_unavailable = True
            health.quota_status = "unavailable"
            log.warning(f"[HEALTH] Provider {provider_id} failure ({error_type}). Cooldown for {cd:.0f}s.")

    def set_missing_models(self, provider_id: str, missing: List[str]) -> None:
        health = self.get_or_create(provider_id)
        health.missing_models = missing

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        """Return dict representation of all provider health states."""
        # Refresh cooldown status before snapshot
        for pid in list(self.health_map.keys()):
            self.is_healthy(pid)
        return {pid: h.to_dict() for pid, h in self.health_map.items()}


health_tracker = ProviderHealthTracker()
