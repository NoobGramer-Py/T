"""
Workflow Automation & Trigger Engine for T AI Operating System.
Evaluates event rules and triggers automated workflow actions.
"""

from typing import Dict, List, Any, Callable, Coroutine
from brain.logging.logger import get_logger

log = get_logger("automation.engine")


class AutomationEngine:
    """Manages automated rule triggers and event workflows."""

    def __init__(self) -> None:
        self._rules: List[Dict[str, Any]] = []

    def add_rule(self, name: str, event_trigger: str, action: Callable[..., Coroutine[Any, Any, None]]) -> None:
        """Adds an event trigger automation rule."""
        self._rules.append({"name": name, "trigger": event_trigger, "action": action})
        log.info(f"Added automation rule '{name}' triggered by '{event_trigger}'")

    async def evaluate_trigger(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Evaluates incoming events against active automation rules."""
        for rule in self._rules:
            if rule["trigger"] == event_name:
                log.info(f"Triggering automation rule '{rule['name']}'")
                try:
                    await rule["action"](payload)
                except Exception as e:
                    log.error(f"Error executing automation rule '{rule['name']}'", exc_info=True)


automation_engine = AutomationEngine()
