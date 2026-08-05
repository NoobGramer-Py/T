"""
Base Skill Contract for T AI Operating System.
Provides standard metadata and execution interfaces for system tools and skills.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class AbstractSkill(ABC):
    """Base interface for all capabilities and skills in T OS."""

    name: str
    description: str
    parameters_schema: Dict[str, Any]

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Any:
        """Executes the skill action."""
        pass
