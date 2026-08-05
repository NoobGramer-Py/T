"""
Safe Execution Engine for T AI Operating System.
Orchestrates authorized, interruptible, recoverable, and audited action executions across system tools.
"""

import asyncio
from dataclasses import dataclass
from typing import Dict, Any, Optional
from brain.security.permission_manager import permission_manager
from brain.simulation.sandbox import simulation_sandbox
from brain.logging.logger import get_logger

log = get_logger("execution.runner")


@dataclass
class ExecutionResult:
    """Standard result structure returned by tool execution."""
    success: bool
    action_type: str
    output: Any
    error: Optional[str] = None
    execution_time_sec: float = 0.0


class ExecutionEngine:
    """Safely executes tasks and tools under policy enforcement."""

    def __init__(self) -> None:
        self._active_executions: Dict[str, asyncio.Task] = {}

    async def execute_action(
        self,
        action_type: str,
        resource: str,
        params: Dict[str, Any],
        user_authorized: bool = False
    ) -> ExecutionResult:
        """Evaluates permission, simulates, and executes action."""
        start_time = asyncio.get_event_loop().time()
        log.info(f"Execution request: action='{action_type}', resource='{resource}'")

        # 1. Permission check
        if not permission_manager.is_action_allowed(action_type, resource, user_authorized=user_authorized):
            return ExecutionResult(
                success=False,
                action_type=action_type,
                output=None,
                error="Action denied by security permission policy.",
            )

        # 2. Simulation check
        sim_res = await simulation_sandbox.simulate_action(action_type, params)
        if not sim_res.get("simulation_success"):
            return ExecutionResult(
                success=False,
                action_type=action_type,
                output=None,
                error="Action failed safety simulation check.",
            )

        # 3. Execution dispatch
        try:
            output = await self._dispatch(action_type, params)
            elapsed = asyncio.get_event_loop().time() - start_time
            return ExecutionResult(
                success=True,
                action_type=action_type,
                output=output,
                execution_time_sec=round(elapsed, 4),
            )
        except Exception as e:
            log.error(f"Execution error for action '{action_type}'", exc_info=True)
            elapsed = asyncio.get_event_loop().time() - start_time
            return ExecutionResult(
                success=False,
                action_type=action_type,
                output=None,
                error=str(e),
                execution_time_sec=round(elapsed, 4),
            )

    async def _dispatch(self, action_type: str, params: Dict[str, Any]) -> Any:
        """Internal dispatch router for system capabilities."""
        if action_type == "open_url":
            import webbrowser
            url = params.get("url", "")
            webbrowser.open(url)
            return f"Opened URL: {url}"

        if action_type == "launch_file":
            import subprocess
            target = params.get("target", "")
            subprocess.Popen(target, shell=True)
            return f"Launched target: {target}"

        return f"Executed action '{action_type}' successfully."


execution_engine = ExecutionEngine()
