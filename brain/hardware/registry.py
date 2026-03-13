"""
Device registry for T's hardware module.
Single source of truth for every physical device T knows about.
Backed by brain/config/hardware_devices.yaml — human-readable and hand-editable.
Loaded once at startup; updated at runtime via register()/unregister().
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from core.logger import get_logger

log = get_logger("hardware.registry")

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "hardware_devices.yaml"


@dataclass
class DeviceConfig:
    id:          str
    type:        Literal["serial", "mqtt", "gpio"]
    description: str                     = ""
    capabilities: list[str]              = field(default_factory=list)
    # Serial / GPIO
    port:        str                     = ""   # COM3 or /dev/ttyUSB0
    baud:        int                     = 9600
    # MQTT
    broker:      str                     = ""
    mqtt_port:   int                     = 1883
    topic_pub:   str                     = ""
    topic_sub:   str                     = ""
    mqtt_user:   str                     = ""
    mqtt_pass:   str                     = ""


# In-memory registry — populated by load()
_registry: dict[str, DeviceConfig] = {}
_loaded   = False


def load() -> None:
    """Load devices from hardware_devices.yaml. Safe to call multiple times."""
    global _loaded
    try:
        import yaml  # pyyaml is already in requirements
        if not _CONFIG_PATH.exists():
            log.info("hardware_devices.yaml not found — no devices registered")
            _loaded = True
            return
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for raw in data.get("devices", []):
            try:
                dev = _from_dict(raw)
                _registry[dev.id] = dev
                log.info(f"device loaded  id={dev.id!r}  type={dev.type}")
            except Exception as e:
                log.warning(f"skipping malformed device entry: {e}  raw={raw}")
        _loaded = True
        log.info(f"hardware registry ready — {len(_registry)} device(s)")
    except Exception as e:
        log.warning(f"hardware registry load failed: {e}")
        _loaded = True


def get(device_id: str) -> DeviceConfig | None:
    _ensure_loaded()
    return _registry.get(device_id)


def list_all() -> list[DeviceConfig]:
    _ensure_loaded()
    return list(_registry.values())


def register(config: dict) -> DeviceConfig:
    """Add or replace a device at runtime and persist to YAML."""
    _ensure_loaded()
    dev = _from_dict(config)
    _registry[dev.id] = dev
    _persist()
    log.info(f"device registered  id={dev.id!r}")
    return dev


def unregister(device_id: str) -> bool:
    """Remove a device by id. Returns True if it existed."""
    _ensure_loaded()
    if device_id not in _registry:
        return False
    del _registry[device_id]
    _persist()
    log.info(f"device unregistered  id={device_id!r}")
    return True


# ─── Internal ─────────────────────────────────────────────────────────────────

def _ensure_loaded() -> None:
    if not _loaded:
        load()


def _from_dict(raw: dict) -> DeviceConfig:
    return DeviceConfig(
        id           = str(raw["id"]),
        type         = str(raw["type"]),
        description  = str(raw.get("description", "")),
        capabilities = list(raw.get("capabilities", [])),
        port         = str(raw.get("port", "")),
        baud         = int(raw.get("baud", 9600)),
        broker       = str(raw.get("broker", "")),
        mqtt_port    = int(raw.get("port_mqtt", raw.get("mqtt_port", 1883))),
        topic_pub    = str(raw.get("topic_pub", "")),
        topic_sub    = str(raw.get("topic_sub", "")),
        mqtt_user    = str(raw.get("mqtt_user", "")),
        mqtt_pass    = str(raw.get("mqtt_pass", "")),
    )


def _to_dict(dev: DeviceConfig) -> dict:
    d: dict = {"id": dev.id, "type": dev.type}
    if dev.description:  d["description"]  = dev.description
    if dev.capabilities: d["capabilities"] = dev.capabilities
    if dev.type in ("serial", "gpio"):
        if dev.port: d["port"] = dev.port
        if dev.baud != 9600: d["baud"] = dev.baud
    if dev.type == "mqtt":
        if dev.broker:    d["broker"]    = dev.broker
        if dev.mqtt_port != 1883: d["port_mqtt"] = dev.mqtt_port
        if dev.topic_pub: d["topic_pub"] = dev.topic_pub
        if dev.topic_sub: d["topic_sub"] = dev.topic_sub
        if dev.mqtt_user: d["mqtt_user"] = dev.mqtt_user
    return d


def _persist() -> None:
    try:
        import yaml
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {"devices": [_to_dict(d) for d in _registry.values()]}
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        log.warning(f"failed to persist hardware registry: {e}")
