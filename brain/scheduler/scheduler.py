"""
Task Scheduler Subsystem for T AI Operating System.
Schedules delayed tasks, one-shot timers, and recurring background jobs.
"""

import asyncio
from dataclasses import dataclass
from typing import Callable, Coroutine, Dict, Any, List
from brain.logging.logger import get_logger

log = get_logger("scheduler")


@dataclass
class ScheduledTask:
    task_id: str
    delay_seconds: float
    coro: Callable[[], Coroutine[Any, Any, None]]


class TaskScheduler:
    """Manages system task timers and scheduled job executions."""

    def __init__(self) -> None:
        self._tasks: Dict[str, asyncio.Task] = {}

    def schedule_delayed(
        self,
        task_id: str,
        delay_seconds: float,
        coro: Callable[[], Coroutine[Any, Any, None]]
    ) -> None:
        """Schedules a delayed execution task."""
        async def _wrapper():
            await asyncio.sleep(delay_seconds)
            log.info(f"Running scheduled task '{task_id}'")
            try:
                await coro()
            except Exception as e:
                log.error(f"Error in scheduled task '{task_id}'", exc_info=True)

        task = asyncio.create_task(_wrapper())
        self._tasks[task_id] = task
        log.info(f"Scheduled task '{task_id}' to run in {delay_seconds}s")

    def cancel_task(self, task_id: str) -> bool:
        """Cancels a pending scheduled task."""
        task = self._tasks.pop(task_id, None)
        if task and not task.done():
            task.cancel()
            log.info(f"Cancelled scheduled task '{task_id}'")
            return True
        return False


task_scheduler = TaskScheduler()
