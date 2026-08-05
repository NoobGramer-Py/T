"""
Diagnostics & System Health Self-Test Subsystem.
Verifies module readiness, dependency status, and system integrity.
"""

from typing import Dict, Any, List
from brain.logging.logger import get_logger

log = get_logger("diagnostics")


class SelfTestRunner:
    """Executes automated diagnostic checks across OS subsystems."""

    async def run_diagnostics(self) -> Dict[str, Any]:
        """Runs a diagnostic battery and reports overall system health."""
        results: Dict[str, Any] = {
            "status": "healthy",
            "passed": 0,
            "failed": 0,
            "checks": {}
        }

        checks = [
            ("config_load", self._check_config),
            ("logging_system", self._check_logging),
            ("telemetry_collector", self._check_telemetry),
        ]

        for check_name, check_fn in checks:
            try:
                success, details = await check_fn()
                results["checks"][check_name] = {"status": "ok" if success else "error", "details": details}
                if success:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    results["status"] = "degraded"
            except Exception as e:
                log.error(f"Diagnostic check failed: {check_name}", exc_info=True)
                results["checks"][check_name] = {"status": "error", "details": str(e)}
                results["failed"] += 1
                results["status"] = "degraded"

        return results

    async def _check_config(self) -> tuple[bool, str]:
        from brain.config.config import config
        return (config is not None, f"Environment: {config.environment}")

    async def _check_logging(self) -> tuple[bool, str]:
        log.debug("Diagnostic log ping")
        return (True, "Logging active")

    async def _check_telemetry(self) -> tuple[bool, str]:
        from brain.telemetry.metrics import metrics
        summary = metrics.get_summary()
        return (isinstance(summary, dict), f"Uptime: {summary.get('uptime_seconds')}s")


diagnostics = SelfTestRunner()
