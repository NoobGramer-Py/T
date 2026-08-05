"""
Dynamic Module Loader for T AI Operating System.
Manages the registration, initialization, startup, and shutdown lifecycle of OS modules.
"""

from typing import Dict, Any, Protocol, runtime_checkable
from brain.logging.logger import get_logger

log = get_logger("core.module_loader")


@runtime_checkable
class OSModule(Protocol):
    """Lifecycle protocol interface that every T OS module can implement."""
    name: str

    async def initialize(self) -> None:
        ...

    async def start(self) -> None:
        ...

    async def shutdown(self) -> None:
        ...


class ModuleLoader:
    """Manages system-wide module discovery, initialization, and lifecycle."""

    def __init__(self) -> None:
        self._modules: Dict[str, Any] = {}

    def register(self, name: str, module_instance: Any) -> None:
        """Registers a module with the loader."""
        self._modules[name] = module_instance
        log.info(f"Registered OS module: '{name}'")

    async def initialize_all(self) -> None:
        """Initializes all registered modules."""
        for name, mod in self._modules.items():
            if hasattr(mod, "initialize") and callable(mod.initialize):
                try:
                    log.info(f"Initializing module '{name}'...")
                    await mod.initialize()
                except Exception as e:
                    log.error(f"Failed initializing module '{name}'", exc_info=True)

    async def shutdown_all(self) -> None:
        """Gracefully shuts down all registered modules."""
        for name, mod in self._modules.items():
            if hasattr(mod, "shutdown") and callable(mod.shutdown):
                try:
                    log.info(f"Shutting down module '{name}'...")
                    await mod.shutdown()
                except Exception as e:
                    log.error(f"Failed shutting down module '{name}'", exc_info=True)

    def get_module(self, name: str) -> Any:
        """Retrieves a registered module by name."""
        return self._modules.get(name)


module_loader = ModuleLoader()
