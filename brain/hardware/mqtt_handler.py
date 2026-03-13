"""
MQTT handler for T's hardware module.
Connects to any MQTT broker (Mosquitto, Home Assistant, etc.).
Incoming messages on subscribed topics are broadcast to all Tauri clients
as hardware_event messages.
"""

import asyncio
import threading
from core.logger import get_logger

log = get_logger("hardware.mqtt")

# Active clients: broker_addr → paho MQTT client
_clients: dict[str, object] = {}
# device_id → broker_addr  (for routing)
_device_broker: dict[str, str] = {}


async def connect(device_id: str, broker: str, port: int = 1883,
                  user: str = "", password: str = "") -> str:
    """
    Connect to an MQTT broker and store the client.
    Returns "OK: connected" or an error string.
    """
    try:
        import paho.mqtt.client as mqtt  # type: ignore
    except ImportError:
        return "[ERROR] paho-mqtt not installed. Run: pip install paho-mqtt"

    broker_key = f"{broker}:{port}"
    if broker_key in _clients:
        _device_broker[device_id] = broker_key
        return f"OK: already connected to {broker}:{port}"

    loop = asyncio.get_event_loop()
    connected_event = threading.Event()
    error_msg: list[str] = []

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            connected_event.set()
        else:
            error_msg.append(f"MQTT connection refused: code {rc}")
            connected_event.set()

    def on_message(client, userdata, msg):
        payload = msg.payload.decode("utf-8", errors="replace")
        dev_id  = userdata.get("device_id", device_id)
        asyncio.run_coroutine_threadsafe(
            _broadcast_event(dev_id, msg.topic, payload),
            loop,
        )

    client = mqtt.Client(userdata={"device_id": device_id})
    client.on_connect = on_connect
    client.on_message = on_message
    if user:
        client.username_pw_set(user, password)

    try:
        def _do_connect():
            client.connect(broker, port, keepalive=60)
            client.loop_start()

        await loop.run_in_executor(None, _do_connect)
        # Wait up to 5s for connection to be established
        await loop.run_in_executor(None, lambda: connected_event.wait(timeout=5.0))

        if error_msg:
            return f"[ERROR] {error_msg[0]}"

        _clients[broker_key] = client
        _device_broker[device_id] = broker_key
        log.info(f"MQTT connected  device={device_id}  broker={broker}:{port}")
        return f"OK: connected to {broker}:{port}"
    except Exception as e:
        return f"[ERROR] MQTT connect failed: {e}"


async def publish(device_id: str, topic: str, payload: str, qos: int = 0) -> str:
    """Publish a message to a topic."""
    client = _get_client(device_id)
    if isinstance(client, str):
        return client  # error string
    try:
        result = client.publish(topic, payload, qos=qos)  # type: ignore
        result.wait_for_publish(timeout=5.0)
        log.info(f"MQTT publish  device={device_id}  topic={topic!r}  payload={payload!r}")
        return f"OK: published '{payload}' to {topic}"
    except Exception as e:
        return f"[ERROR] MQTT publish failed: {e}"


async def subscribe(device_id: str, topic: str) -> str:
    """Subscribe to a topic. Incoming messages will be broadcast as hardware_event."""
    client = _get_client(device_id)
    if isinstance(client, str):
        return client
    try:
        client.subscribe(topic)  # type: ignore
        log.info(f"MQTT subscribed  device={device_id}  topic={topic!r}")
        return f"OK: subscribed to {topic}"
    except Exception as e:
        return f"[ERROR] MQTT subscribe failed: {e}"


async def disconnect(device_id: str) -> str:
    """Disconnect from the broker associated with this device."""
    broker_key = _device_broker.pop(device_id, None)
    if not broker_key:
        return f"Device '{device_id}' not connected via MQTT."
    # Only truly disconnect if no other device uses this broker
    still_used = any(v == broker_key for v in _device_broker.values())
    if not still_used:
        client = _clients.pop(broker_key, None)
        if client:
            try:
                client.loop_stop()  # type: ignore
                client.disconnect()  # type: ignore
            except Exception:
                pass
    return "OK: MQTT disconnected"


# ─── Internal ─────────────────────────────────────────────────────────────────

def _get_client(device_id: str):
    """Return the paho client for a device, or an error string."""
    broker_key = _device_broker.get(device_id)
    if not broker_key:
        return f"[ERROR] Device '{device_id}' not connected. Connect first."
    client = _clients.get(broker_key)
    if not client:
        return f"[ERROR] MQTT client lost for {broker_key}."
    return client


async def _broadcast_event(device_id: str, topic: str, payload: str) -> None:
    """Forward an incoming MQTT message to all connected Tauri clients."""
    try:
        from core.ws_server import broadcast
        await broadcast({
            "type":      "hardware_event",
            "device_id": device_id,
            "topic":     topic,
            "payload":   payload,
        })
    except Exception as e:
        log.warning(f"MQTT broadcast error: {e}")
