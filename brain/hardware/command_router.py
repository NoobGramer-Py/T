"""
Command router for T's hardware module.
Single entry point from engine.py.
Validates, safety-checks, routes to the correct handler, and returns results.
"""

import asyncio
import json
from typing import TYPE_CHECKING
from .registry       import get as get_device, list_all, register, unregister, load
from .safety         import check_rate_limit, check_pin, is_destructive, is_read
from .serial_handler import discover, connect as serial_connect, send_command, is_connected
from .mqtt_handler   import (
    connect as mqtt_connect, publish as mqtt_publish,
    subscribe as mqtt_subscribe,
)
from .gpio_handler   import set_pin, read_pin, pwm
from core.logger     import get_logger

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("hardware.router")

# Pending confirmation futures: client_id → Future[bool]
_pending_confirms: dict[str, asyncio.Future] = {}


async def handle_hardware_command(client: "Client", msg: dict) -> None:
    """
    Entry point from engine.py for all hardware messages.
    msg.action can be:
      list, discover, connect, disconnect, send,
      digital_write, digital_read, analog_read, dht,
      pwm, publish, subscribe, register, unregister
    """
    action    = msg.get("action", "").lower()
    device_id = msg.get("device_id", "")

    # ── Load registry on first call ───────────────────────────────────────────
    load()

    # ── Special actions (no device required) ─────────────────────────────────
    if action == "list":
        devices = [
            {
                "id":          d.id,
                "type":        d.type,
                "description": d.description,
                "capabilities": d.capabilities,
                "connected":   is_connected(d.id),
            }
            for d in list_all()
        ]
        await client.send({"type": "hardware_devices", "devices": devices})
        return

    if action == "discover":
        ports = discover()
        await client.send({"type": "hardware_devices", "devices": [], "serial_ports": ports})
        return

    if action == "register":
        try:
            dev = register(msg.get("config", {}))
            await client.send({"type": "hardware_result", "device_id": dev.id, "result": f"Registered: {dev.id}"})
        except Exception as e:
            await client.send({"type": "hardware_error", "error": str(e)})
        return

    if action == "unregister":
        ok = unregister(device_id)
        await client.send({
            "type":   "hardware_result",
            "device_id": device_id,
            "result": f"{'Unregistered' if ok else 'Not found'}: {device_id}",
        })
        return

    # ── Device-scoped actions ─────────────────────────────────────────────────
    device = get_device(device_id)
    if not device:
        await client.send({
            "type":  "hardware_error",
            "error": f"Unknown device '{device_id}'. Run 'list devices' to see registered devices.",
        })
        return

    # ── Rate limit ────────────────────────────────────────────────────────────
    try:
        check_rate_limit(device_id)
    except RuntimeError as e:
        await client.send({"type": "hardware_error", "error": str(e)})
        return

    # ── Pin safety ────────────────────────────────────────────────────────────
    pin_raw = msg.get("pin") or msg.get("params", {}).get("pin")
    if pin_raw is not None:
        try:
            check_pin(int(pin_raw))
        except RuntimeError as e:
            await client.send({"type": "hardware_error", "error": str(e)})
            return

    # ── Confirmation for destructive actions ──────────────────────────────────
    if is_destructive(action):
        confirmed = await _request_confirmation(client, device_id, action, msg)
        if not confirmed:
            await client.send({
                "type":      "hardware_result",
                "device_id": device_id,
                "result":    f"Action '{action}' on '{device_id}' was cancelled.",
            })
            return

    # ── Route to handler ──────────────────────────────────────────────────────
    try:
        result = await _dispatch(device, action, msg)
    except Exception as e:
        result = f"[ERROR] {e}"

    if result.startswith("[ERROR]"):
        await client.send({"type": "hardware_error", "device_id": device_id, "error": result})
    else:
        await client.send({
            "type":      "hardware_result",
            "device_id": device_id,
            "action":    action,
            "result":    result,
        })
        log.info(f"hardware command  device={device_id}  action={action}  result={result[:80]}")


async def handle_hardware_confirm(client: "Client", msg: dict) -> None:
    """Resolve a pending hardware confirmation future."""
    fut = _pending_confirms.pop(client.id, None)
    if fut and not fut.done():
        fut.set_result(bool(msg.get("confirmed", False)))


# ─── Internal ─────────────────────────────────────────────────────────────────

async def _dispatch(device, action: str, msg: dict) -> str:
    """Route action to the correct handler function."""
    params = msg.get("params", {})

    # ── Connect ───────────────────────────────────────────────────────────────
    if action == "connect":
        if device.type in ("serial", "gpio"):
            return await serial_connect(
                device.id,
                params.get("port", device.port),
                int(params.get("baud", device.baud)),
            )
        if device.type == "mqtt":
            return await mqtt_connect(
                device.id, device.broker, device.mqtt_port,
                device.mqtt_user, device.mqtt_pass,
            )

    # ── Serial / GPIO commands ────────────────────────────────────────────────
    if action in ("digital_write", "dwrite", "set_pin"):
        pin   = int(params.get("pin",   msg.get("pin",   0)))
        state = str(params.get("state", msg.get("value", "LOW"))).upper()
        if device.type == "gpio":
            return await set_pin(device.id, pin, state)
        return await send_command(device.id, "DWRITE", f"{pin} {state}")

    if action in ("digital_read", "dread", "read_pin"):
        pin = int(params.get("pin", msg.get("pin", 0)))
        if device.type == "gpio":
            return await read_pin(device.id, pin)
        return await send_command(device.id, "DREAD", str(pin))

    if action in ("analog_read", "aread"):
        pin = params.get("pin", msg.get("pin", "A0"))
        return await send_command(device.id, "AREAD", str(pin))

    if action in ("dht", "dht_read", "temperature", "humidity"):
        pin = int(params.get("pin", msg.get("pin", 2)))
        return await send_command(device.id, "DHT", str(pin))

    if action == "pwm":
        pin      = int(params.get("pin",        msg.get("pin", 0)))
        freq     = int(params.get("frequency",  msg.get("frequency", 1000)))
        duty     = int(params.get("duty_cycle", msg.get("duty_cycle", 128)))
        if device.type == "gpio":
            return await pwm(device.id, pin, freq, duty)
        return await send_command(device.id, "PWM", f"{pin} {duty}")

    if action == "ping":
        return await send_command(device.id, "PING")

    if action == "send":
        raw = params.get("command", msg.get("command", ""))
        return await send_command(device.id, raw)

    # ── MQTT commands ─────────────────────────────────────────────────────────
    if action in ("publish", "mqtt_publish"):
        topic   = params.get("topic",   msg.get("topic",   device.topic_pub))
        payload = params.get("payload", msg.get("payload", ""))
        qos     = int(params.get("qos", 0))
        return await mqtt_publish(device.id, topic, payload, qos)

    if action == "subscribe":
        topic = params.get("topic", msg.get("topic", device.topic_sub))
        return await mqtt_subscribe(device.id, topic)

    return f"[ERROR] Unknown action '{action}' for device type '{device.type}'"


async def _request_confirmation(
    client: "Client", device_id: str, action: str, msg: dict
) -> bool:
    """Send hardware_confirm event and await the user's YES/NO response (60s timeout)."""
    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    _pending_confirms[client.id] = fut

    params  = msg.get("params", {})
    pin_val = msg.get("pin") or params.get("pin", "")
    state   = msg.get("value") or msg.get("state") or params.get("state", "") or params.get("payload", "")

    detail = f"{action.upper()}"
    if pin_val:   detail += f" pin {pin_val}"
    if state:     detail += f" → {state}"

    await client.send({
        "type":      "hardware_confirm",
        "device_id": device_id,
        "action":    action,
        "detail":    detail,
        "message":   f"About to execute: {detail} on device '{device_id}'. Confirm?",
    })

    try:
        return await asyncio.wait_for(fut, timeout=60.0)
    except asyncio.TimeoutError:
        return False
    finally:
        _pending_confirms.pop(client.id, None)
