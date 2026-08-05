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
