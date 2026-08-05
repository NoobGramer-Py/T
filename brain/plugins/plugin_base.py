"""
Abstract Plugin Contract for T AI Operating System.
Enables external modular capability extensions without core kernel modifications.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class AbstractPlugin(ABC):
    """Base plugin class that all external T capabilities must implement."""

    name: str
    version: str
    description: str

    @abstractmethod
    async def initialize(self) -> None:
        """Called when plugin is loaded into system."""
        pass

    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Executes a plugin capability action."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean shutdown hook for plugin."""
        pass
