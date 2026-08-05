"""
Asynchronous Event Bus for T AI Operating System.
Enables loosely-coupled publish-subscribe communication across all OS modules.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Callable, Coroutine, Dict, List, Any
from brain.logging.logger import get_logger

log = get_logger("core.event_bus")


@dataclass
class Event:
    """Standardized OS Event data model."""
    name: str
    sender: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0.0)


EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """Central event router supporting asynchronous event subscriptions and publishing."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._global_subscribers: List[EventHandler] = []

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Subscribes an async handler function to a specific event name."""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(handler)
        log.debug(f"Subscribed handler to event '{event_name}'")

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribes an async handler to receive ALL published events."""
        self._global_subscribers.append(handler)

    async def publish(self, event: Event) -> None:
        """Publishes an event to all matching subscribers asynchronously."""
        log.debug(f"Publishing event '{event.name}' from '{event.sender}'")
        handlers = self._subscribers.get(event.name, []) + self._global_subscribers

        if not handlers:
            return

        tasks = [asyncio.create_task(h(event)) for h in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                log.error(f"Error executing event handler for '{event.name}'", exc_info=res)


event_bus = EventBus()
