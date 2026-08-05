"""
Hardware Device Registry & Abstraction Subsystem.
Manages discovered physical and virtual device nodes across the T AI Operating System ecosystem.
"""

from typing import Dict, List, Optional
from brain.devices.base import AbstractDevice
from brain.devices.types import DeviceMetadata, DeviceCategory, ConnectionState
from brain.logging.logger import get_logger

log = get_logger("devices.registry")


class DeviceRegistry:
    """Central registry tracking all active connected hardware devices."""

    def __init__(self) -> None:
        self._devices: Dict[str, AbstractDevice] = {}

    def register_device(self, device: AbstractDevice) -> None:
        """Registers a device implementation in the OS registry."""
        dev_id = device.metadata.device_id
        self._devices[dev_id] = device
        log.info(f"Registered hardware device: '{device.metadata.name}' (Category: {device.metadata.category.value})")

    def unregister_device(self, device_id: str) -> Optional[AbstractDevice]:
        """Removes a device entry from the registry."""
        return self._devices.pop(device_id, None)

    def get_device(self, device_id: str) -> Optional[AbstractDevice]:
        """Retrieves a registered device instance by ID."""
        return self._devices.get(device_id)

    def list_devices(self, category: Optional[DeviceCategory] = None) -> List[DeviceMetadata]:
        """Returns list of registered device metadata entries."""
        if category is None:
            return [d.metadata for d in self._devices.values()]
        return [d.metadata for d in self._devices.values() if d.metadata.category == category]


device_registry = DeviceRegistry()
