"""
REST API Subsystem for T AI Operating System.
Exposes standard HTTP REST endpoints for client applications, edge nodes, and hardware controllers.
"""

from fastapi import APIRouter
from brain.core.engine import kernel
from brain.core.state_manager import state_manager
from brain.core.health_monitor import health_monitor
from brain.telemetry.metrics import metrics
from brain.diagnostics.self_test import diagnostics

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/status")
async def get_system_status():
    """Returns system operational state and kernel readiness."""
    return state_manager.snapshot()


@api_router.get("/health")
async def get_system_health():
    """Returns detailed health status for registered modules."""
    return health_monitor.get_system_health()


@api_router.get("/metrics")
async def get_system_metrics():
    """Returns system performance and execution metrics."""
    return metrics.get_summary()


@api_router.get("/diagnostics")
async def run_diagnostics():
    """Executes a diagnostic self-test suite and returns results."""
    return await diagnostics.run_diagnostics()


@api_router.get("/models/status")
async def get_models_status():
    """Returns provider health, registered model metadata, and model routing state."""
    from brain.core.provider_health import health_tracker
    from brain.core.model_registry import model_registry
    from brain.config.config import config

    models = model_registry.get_all_models()
    providers = []

    for pid, p in model_registry.providers.items():
        is_cfg = await p.is_available()
        providers.append({
            "id": pid,
            "name": p.name,
            "configured": is_cfg,
            "maskedKey": p.mask_key(getattr(config.model, f"{pid}_api_key", None) or config.model.api_key),
        })

    return {
        "providers": providers,
        "health": health_tracker.snapshot(),
        "models": [
            {
                "provider": m.provider,
                "model": m.model,
                "capabilities": m.capabilities,
                "contextWindow": m.context_window,
                "priority": m.priority,
                "enabled": m.enabled,
                "local": m.local,
            }
            for m in models
        ],
        "localPreferred": config.model.local_preferred,
        "fallbackOrder": config.model.fallback_order,
    }


@api_router.post("/models/config")
async def update_models_config(data: dict):
    """Updates model routing settings at runtime."""
    from brain.config.config import config
    from brain.core.model_router import model_router

    if "localPreferred" in data:
        config.model.local_preferred = bool(data["localPreferred"])
    if "fallbackOrder" in data and isinstance(data["fallbackOrder"], list):
        config.model.fallback_order = data["fallbackOrder"]
    if "apiKeys" in data and isinstance(data["apiKeys"], dict):
        for k, v in data["apiKeys"].items():
            if hasattr(config.model, f"{k}_api_key"):
                setattr(config.model, f"{k}_api_key", v)

    # Re-initialize providers with updated keys/settings
    model_router._initialized = False
    await model_router.initialize()

    return {"status": "updated", "config": {
        "localPreferred": config.model.local_preferred,
        "fallbackOrder": config.model.fallback_order,
    }}

