"""
Central System State Manager for T AI Operating System.
Maintains state across system components and emits state-change events.
"""

from typing import Dict, Any, Optional
from brain.core.event_bus import event_bus, Event
from brain.logging.logger import get_logger

log = get_logger("core.state")


class StateManager:
    """Thread-safe system state store with event notification support."""

    def __init__(self) -> None:
        self._state: Dict[str, Any] = {
            "status": "initializing",
            "active_tasks": 0,
            "connected_clients": 0,
            "connected_devices": 0,
            "current_mode": "normal",
        }

    def set(self, key: str, value: Any, sender: str = "core.state") -> None:
        """Sets a state property and triggers a state-changed event if updated."""
        old_val = self._state.get(key)
        if old_val != value:
            self._state[key] = value
            log.debug(f"State changed: {key} = {value}")
            # Non-blocking publish task if event loop is running
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(event_bus.publish(Event(
                    name="state_changed",
                    sender=sender,
                    data={"key": key, "old": old_val, "new": value}
                )))
            except RuntimeError:
                pass

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a state value."""
        return self._state.get(key, default)

    def snapshot(self) -> Dict[str, Any]:
        """Returns a copy of the entire system state."""
        return self._state.copy()


state_manager = StateManager()
