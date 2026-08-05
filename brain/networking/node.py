"""
Distributed Host Node Specification for T AI Operating System.
Represents an instance host running T OS (PC, Edge Node, Drone Host, MCU gateway).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class OSNode:
    """Represents a remote or local T OS host instance node."""
    node_id: str
    host: str
    port: int
    is_primary: bool = False
    status: str = "online"
    capabilities: List[str] = field(default_factory=list)
