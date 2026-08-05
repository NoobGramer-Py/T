"""
Skill Registry & Capability Router for T AI Operating System.
Tracks available system skills and handles execution requests.
"""

from typing import Dict, List, Optional, Any
from brain.skills.base import AbstractSkill
from brain.logging.logger import get_logger

log = get_logger("skills.registry")


class SkillRegistry:
    """Registry tracking operational capabilities and skills."""

    def __init__(self) -> None:
        self._skills: Dict[str, AbstractSkill] = {}

    def register(self, skill: AbstractSkill) -> None:
        """Registers a skill into T OS."""
        self._skills[skill.name] = skill
        log.info(f"Registered skill: '{skill.name}'")

    def get_skill(self, name: str) -> Optional[AbstractSkill]:
        """Retrieves a skill instance by name."""
        return self._skills.get(name)

    def list_skills(self) -> List[Dict[str, Any]]:
        """Lists registered skills and schemas."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "schema": getattr(s, "parameters_schema", {}),
            }
            for s in self._skills.values()
        ]


skill_registry = SkillRegistry()
