"""
Proactive engine for T.
Started once at brain boot as a background asyncio task.
Polls system monitors every 30s, fires due scheduled reminders,
and broadcasts all alerts to connected Tauri clients.
"""

import asyncio
from .monitor     import SystemMonitor
from .alerts      import AlertManager
from .suggestions import SuggestionEngine
from core.logger  import get_logger

log = get_logger("proactive.engine")

_POLL_INTERVAL = 30   # seconds between monitor polls

_monitor     = SystemMonitor()
_alert_mgr   = AlertManager()
_suggestions = SuggestionEngine()
_running     = False


async def start() -> None:
    """
    Start the proactive engine background loop.
    Safe to call multiple times — only one loop runs.
    """
    global _running
    if _running:
        return
    _running = True
    asyncio.create_task(_loop(), name="proactive_engine")
    log.info("proactive engine started")


async def _loop() -> None:
    from core.ws_server import broadcast
    while _running:
        try:
            await _tick(broadcast)
        except Exception as e:
            log.warning(f"proactive tick error: {e}")
        await asyncio.sleep(_POLL_INTERVAL)


async def _tick(broadcast_fn) -> None:
    # Run monitor.check() in a thread — psutil calls are blocking I/O
    loop      = asyncio.get_event_loop()
    anomalies = await loop.run_in_executor(None, _monitor.check)

    # ── System monitor anomalies ──────────────────────────────────────────────
    for a in anomalies:
        # Use a stable cooldown key so same anomaly doesn't spam
        key = f"monitor:{a.kind}:{a.message[:40]}"
        if _alert_mgr.should_fire(key, cooldown_minutes=10):
            await broadcast_fn({
                "type":     "proactive_alert",
                "severity": a.severity,
                "message":  a.message,
            })
            log.info(f"alert fired  kind={a.kind}  severity={a.severity}")

    # ── Scheduled reminders ───────────────────────────────────────────────────
    for alert in _alert_mgr.pop_due():
        await broadcast_fn({
            "type":     "proactive_alert",
            "severity": "info",
            "message":  f"Reminder: {alert.message}",
        })
        log.info(f"reminder fired  id={alert.id!r}")


# ─── Public API (called from engine.py) ──────────────────────────────────────

def observe_message(user_message: str) -> str | None:
    """
    Observe a user message for pattern-based suggestions.
    Returns a suggestion string if one is warranted, else None.
    Call from engine.py after every user message.
    """
    return _suggestions.observe(user_message)


def schedule_reminder(alert_id: str, message: str, fire_at: float) -> None:
    """Schedule a reminder to fire at a Unix timestamp."""
    _alert_mgr.schedule(alert_id, message, fire_at)


def cancel_reminder(alert_id: str) -> bool:
    """Cancel a pending reminder by id."""
    return _alert_mgr.cancel(alert_id)
