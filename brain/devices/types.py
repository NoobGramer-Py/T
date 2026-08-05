"""
Device Type & Status Specifications for T AI Operating System.
Provides enum and data contracts for abstract hardware hosts (Robots, Drones, Microcontrollers, Wearables, IoT).
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


class DeviceCategory(str, Enum):
    ROBOT = "robot"
    DRONE = "drone"
    MICROCONTROLLER = "microcontroller" # ESP32, Arduino, STM32
    WEARABLE = "wearable"
    CAMERA = "camera"
    MICROPHONE = "microphone"
    SPEAKER = "speaker"
    DISPLAY = "display"
    IOT_SENSOR = "iot_sensor"
    VEHICLE = "vehicle"
    COMPUTER_HOST = "computer_host"


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class DeviceMetadata:
    device_id: str
    name: str
    category: DeviceCategory
    host_address: str
    capabilities: list[str] = field(default_factory=list)
    connection_state: ConnectionState = ConnectionState.DISCONNECTED
    telemetry: Dict[str, Any] = field(default_factory=dict)
