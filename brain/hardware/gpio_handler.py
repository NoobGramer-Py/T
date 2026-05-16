"""
GPIO handler for T's hardware module.
On Raspberry Pi: uses RPi.GPIO directly.
On all other systems: forwards GPIO commands to the first registered serial device.
"""

import asyncio
import sys
from core.logger import get_logger

log = get_logger("hardware.gpio")


def is_rpi() -> bool:
    """Return True if running on a Raspberry Pi."""
    try:
        if sys.platform != "linux":
            return False
        with open("/proc/cpuinfo", "r") as f:
            return "Raspberry Pi" in f.read()
    except Exception:
        return False


async def set_pin(device_id: str, pin: int, state: str) -> str:
    """
    Set a GPIO pin HIGH or LOW.
    On RPi: direct GPIO. Otherwise: serial DWRITE command.
    state: "HIGH" or "LOW" (case-insensitive).
    """
    state = state.upper()
    if state not in ("HIGH", "LOW"):
        return f"[ERROR] Invalid state '{state}'. Use HIGH or LOW."

    if is_rpi():
        return await _rpi_digital_write(pin, state)
    else:
        from hardware.serial_handler import send_command
        return await send_command(device_id, "DWRITE", f"{pin} {state}")


async def read_pin(device_id: str, pin: int) -> str:
    """
    Read a GPIO pin state.
    On RPi: direct GPIO. Otherwise: serial DREAD command.
    """
    if is_rpi():
        return await _rpi_digital_read(pin)
    else:
        from hardware.serial_handler import send_command
        return await send_command(device_id, "DREAD", str(pin))


async def pwm(device_id: str, pin: int, frequency: int, duty_cycle: int) -> str:
    """
    Set PWM output on a pin.
    duty_cycle: 0–255.
    On RPi: direct GPIO PWM. Otherwise: serial PWM command.
    """
    if is_rpi():
        return await _rpi_pwm(pin, frequency, duty_cycle)
    else:
        from hardware.serial_handler import send_command
        return await send_command(device_id, "PWM", f"{pin} {duty_cycle}")


# ─── RPi GPIO ────────────────────────────────────────────────────────────────

async def _rpi_digital_write(pin: int, state: str) -> str:
    def _run():
        try:
            import RPi.GPIO as GPIO  # type: ignore
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH if state == "HIGH" else GPIO.LOW)
            return f"OK: pin {pin} set to {state}"
        except ImportError:
            return "[ERROR] RPi.GPIO not installed. Run: pip install RPi.GPIO"
        except Exception as e:
            return f"[ERROR] GPIO write failed: {e}"
    return await asyncio.get_event_loop().run_in_executor(None, _run)


async def _rpi_digital_read(pin: int) -> str:
    def _run():
        try:
            import RPi.GPIO as GPIO  # type: ignore
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.IN)
            val = GPIO.input(pin)
            return f"OK: pin {pin} is {'HIGH' if val else 'LOW'}"
        except ImportError:
            return "[ERROR] RPi.GPIO not installed. Run: pip install RPi.GPIO"
        except Exception as e:
            return f"[ERROR] GPIO read failed: {e}"
    return await asyncio.get_event_loop().run_in_executor(None, _run)


async def _rpi_pwm(pin: int, frequency: int, duty_cycle: int) -> str:
    def _run():
        try:
            import RPi.GPIO as GPIO  # type: ignore
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.OUT)
            p = GPIO.PWM(pin, frequency)
            p.start(duty_cycle / 255 * 100)  # convert 0–255 to 0–100%
            return f"OK: PWM on pin {pin} — freq={frequency}Hz duty={duty_cycle}/255"
        except ImportError:
            return "[ERROR] RPi.GPIO not installed. Run: pip install RPi.GPIO"
        except Exception as e:
            return f"[ERROR] PWM failed: {e}"
    return await asyncio.get_event_loop().run_in_executor(None, _run)
