"""
Hardware safety layer for T.
Enforces three hard rules before any command reaches a device:
  1. Rate limiting — no device can receive more than 10 commands per 10 seconds
  2. Pin blocklist — pins 0 and 1 on Arduino are blocked (serial TX/RX)
  3. Destructive-action flag — write/set/publish/send/reset/power require confirmation
"""

import time
from collections import defaultdict
from core.logger import get_logger

log = get_logger("hardware.safety")

# ─── Constants ────────────────────────────────────────────────────────────────

_RATE_MAX       = 10    # max commands per window per device
_RATE_WINDOW_S  = 10    # rolling window in seconds

_PIN_BLOCKLIST  = {0, 1}  # Arduino serial TX/RX — never write these

_DESTRUCTIVE_ACTIONS = {
    "digital_write", "dwrite", "set_pin",
    "pwm",
    "publish", "send", "mqtt_publish",
    "reset", "power", "power_on", "power_off",
    "write_file",
}

_READ_ACTIONS = {
    "digital_read", "dread", "read_pin",
    "analog_read", "aread",
    "dht_read", "dht", "temperature", "humidity",
    "ping", "status", "list", "discover",
}


# ─── Rate limiter ─────────────────────────────────────────────────────────────

class _RateLimiter:
    def __init__(self) -> None:
        # device_id → list of Unix timestamps for each command
        self._windows: dict[str, list[float]] = defaultdict(list)

    def check(self, device_id: str) -> None:
        """
        Raise RuntimeError if this device has hit the rate limit.
        Cleans up stale entries on every call.
        """
        now  = time.time()
        hits = self._windows[device_id]
        # Trim entries outside the rolling window
        self._windows[device_id] = [t for t in hits if now - t < _RATE_WINDOW_S]
        if len(self._windows[device_id]) >= _RATE_MAX:
            raise RuntimeError(
                f"Rate limit: device '{device_id}' received {_RATE_MAX}+ commands "
                f"in {_RATE_WINDOW_S}s. Wait before sending more."
            )
        self._windows[device_id].append(now)


_rate_limiter = _RateLimiter()


# ─── Public API ───────────────────────────────────────────────────────────────

def check_rate_limit(device_id: str) -> None:
    """Raise RuntimeError if rate limit exceeded for this device."""
    _rate_limiter.check(device_id)


def check_pin(pin: int) -> None:
    """Raise RuntimeError if the pin is on the blocklist."""
    if pin in _PIN_BLOCKLIST:
        raise RuntimeError(
            f"Pin {pin} is blocked (Arduino serial TX/RX). "
            f"Blocked pins: {sorted(_PIN_BLOCKLIST)}."
        )


def is_destructive(action: str) -> bool:
    """Return True if this action requires explicit confirmation before execution."""
    return action.lower() in _DESTRUCTIVE_ACTIONS


def is_read(action: str) -> bool:
    """Return True if this action is read-only (no confirmation needed)."""
    return action.lower() in _READ_ACTIONS
