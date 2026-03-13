"""
Alert management for T's proactive engine.
  - Cooldown tracking: no alert fires more than once per N minutes per kind
  - Scheduled reminders: time-based alerts set by Abdul via chat
"""

import time
from dataclasses import dataclass, field
from core.logger import get_logger

log = get_logger("proactive.alerts")


@dataclass
class ScheduledAlert:
    id:      str
    message: str
    fire_at: float   # Unix timestamp
    fired:   bool    = False


class AlertManager:
    def __init__(self) -> None:
        self._cooldowns: dict[str, float]     = {}  # kind → last_fired_ts
        self._scheduled: list[ScheduledAlert] = []

    def should_fire(self, kind: str, cooldown_minutes: int = 10) -> bool:
        """
        Returns True if enough time has passed since this kind last fired.
        Records the current time as the new last-fired timestamp.
        """
        now  = time.time()
        last = self._cooldowns.get(kind, 0.0)
        if now - last >= cooldown_minutes * 60:
            self._cooldowns[kind] = now
            return True
        return False

    def schedule(self, alert_id: str, message: str, fire_at: float) -> None:
        """Schedule a future reminder."""
        self._scheduled.append(ScheduledAlert(id=alert_id, message=message, fire_at=fire_at))
        log.info(f"alert scheduled  id={alert_id!r}  fire_at={fire_at}")

    def cancel(self, alert_id: str) -> bool:
        """Cancel a pending scheduled alert by id. Returns True if found."""
        before = len(self._scheduled)
        self._scheduled = [a for a in self._scheduled if a.id != alert_id]
        return len(self._scheduled) < before

    def pop_due(self) -> list[ScheduledAlert]:
        """
        Return all alerts whose fire_at has passed and that haven't fired yet.
        Marks them as fired. Prunes stale fired alerts older than 1 hour.
        """
        now = time.time()
        due = [a for a in self._scheduled if not a.fired and a.fire_at <= now]
        for a in due:
            a.fired = True
        self._scheduled = [
            a for a in self._scheduled
            if not a.fired or (now - a.fire_at < 3600)
        ]
        return due
