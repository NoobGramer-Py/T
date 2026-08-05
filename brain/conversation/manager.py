"""
Conversation & Dialogue Manager for T AI Operating System.
Handles language generation context assembly, response formatting, and dialogue state.
"""

from typing import Dict, Any, List
from brain.memory.short_term import short_term_memory
from brain.logging.logger import get_logger

log = get_logger("conversation.manager")


class DialogueManager:
    """Manages dialogue flows and context formatting for natural language outputs."""

    def format_prompt_context(self, memory_context: Dict[str, Any]) -> str:
        """Formats memory snapshots into clean prompt context strings."""
        parts = []
        if memory_context.get("knowledge_docs"):
            parts.append("### Relevant Project Knowledge:")
            for doc in memory_context["knowledge_docs"]:
                parts.append(f"- **{doc['title']}**: {doc['content']}")

        if memory_context.get("user_preferences"):
            parts.append("### User Settings & Preferences:")
            for k, v in memory_context["user_preferences"].items():
                parts.append(f"- {k}: {v}")

        return "\n".join(parts)


dialogue_manager = DialogueManager()
