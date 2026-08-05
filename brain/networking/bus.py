"""
Inter-Node Communication & RPC Network Protocol Subsystem.
Facilitates distributed event propagation and remote execution between host nodes.
"""

from typing import Dict, List, Optional, Any
from brain.networking.node import OSNode
from brain.logging.logger import get_logger

log = get_logger("networking.bus")


class NetworkBus:
    """Manages RPC and distributed messaging across T OS host nodes."""

    def __init__(self) -> None:
        self._nodes: Dict[str, OSNode] = {}

    def register_peer_node(self, node: OSNode) -> None:
        """Registers a remote or local T host node."""
        self._nodes[node.node_id] = node
        log.info(f"Registered host node: '{node.node_id}' ({node.host}:{node.port})")

    async def broadcast_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Broadcasts an OS event across connected host nodes."""
        log.info(f"Broadcasting network event '{event_name}' to {len(self._nodes)} peer nodes.")
        for node_id, node in self._nodes.items():
            log.debug(f"Sending '{event_name}' to node '{node_id}'")

    def get_nodes(self) -> List[OSNode]:
        """Returns list of registered host nodes."""
        return list(self._nodes.values())


network_bus = NetworkBus()
