"""
Base Device Interface Contract for T AI Operating System.
Defines abstract lifecycle methods that all host hardware implementations must conform to.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from brain.devices.types import DeviceMetadata, ConnectionState


class AbstractDevice(ABC):
    """Abstract interface that every physical or virtual device subclass implements."""

    def __init__(self, metadata: DeviceMetadata) -> None:
        self.metadata = metadata

    @abstractmethod
    async def connect(self) -> bool:
        """Establishes connection to the target device host."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Terminates connection cleanly."""
        pass

    @abstractmethod
    async def send_command(self, command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sends an operational command to the device."""
        pass

    @abstractmethod
    async def read_telemetry(self) -> Dict[str, Any]:
        """Reads current telemetry metrics from device sensors."""
        pass
