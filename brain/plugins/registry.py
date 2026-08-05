"""
Dynamic Plugin Registry & Lifecycle Subsystem.
Registers, verifies, and executes dynamically loaded plugins.
"""

from typing import Dict, List, Optional
from brain.plugins.plugin_base import AbstractPlugin
from brain.logging.logger import get_logger

log = get_logger("plugins.registry")


class PluginRegistry:
    """Manages system plugin lifecycle and execution."""

    def __init__(self) -> None:
        self._plugins: Dict[str, AbstractPlugin] = {}

    async def register_plugin(self, plugin: AbstractPlugin) -> bool:
        """Initializes and registers a plugin into T OS."""
        try:
            await plugin.initialize()
            self._plugins[plugin.name] = plugin
            log.info(f"Registered plugin: '{plugin.name}' (v{plugin.version})")
            return True
        except Exception as e:
            log.error(f"Failed to load plugin '{getattr(plugin, 'name', 'unknown')}'", exc_info=True)
            return False

    def get_plugin(self, name: str) -> Optional[AbstractPlugin]:
        """Retrieves a registered plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> List[Dict[str, str]]:
        """Lists registered plugins and metadata."""
        return [{"name": p.name, "version": p.version, "description": p.description} for p in self._plugins.values()]


plugin_registry = PluginRegistry()
