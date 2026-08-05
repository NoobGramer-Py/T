"""
Health and Module Lifecycle Monitor for T AI Operating System.
Monitors module readiness, heartbeat statuses, and resource health.
"""

from typing import Dict, Any
from brain.logging.logger import get_logger

log = get_logger("core.health")


class HealthMonitor:
    """Monitors individual subsystem readiness and health statuses."""

    def __init__(self) -> None:
        self._module_statuses: Dict[str, Dict[str, Any]] = {}

    def register_module(self, name: str) -> None:
        """Registers a subsystem for health monitoring."""
        self._module_statuses[name] = {"status": "registered", "health": "ok", "last_heartbeat": 0}
        log.info(f"Registered module '{name}' for health monitoring.")

    def update_status(self, name: str, status: str, health: str = "ok") -> None:
        """Updates health and operational status for a module."""
        if name not in self._module_statuses:
            self.register_module(name)
        self._module_statuses[name]["status"] = status
        self._module_statuses[name]["health"] = health

    def get_system_health(self) -> Dict[str, Any]:
        """Returns overall system and per-module health breakdown."""
        overall = "healthy"
        for mod, info in self._module_statuses.items():
            if info["health"] != "ok":
                overall = "degraded"
                break
        return {
            "overall_status": overall,
            "modules": self._module_statuses.copy()
        }


health_monitor = HealthMonitor()
