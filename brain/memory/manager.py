"""
Unified Memory Subsystem Manager for T AI Operating System.
Coordinates short-term, working, long-term, and preference memory layers under a single API.
"""

from typing import Dict, Any, List, Optional
from brain.memory.short_term import short_term_memory, ShortTermMemory
from brain.memory.working_memory import working_memory, WorkingMemory
from brain.memory.long_term import long_term_memory, LongTermMemory
from brain.memory.preferences import user_preferences, UserPreferencesStore


class MemoryManager:
    """Coordinates multi-layered memory architecture across T OS."""

    def __init__(self) -> None:
        self.short_term = short_term_memory
        self.working = working_memory
        self.long_term = long_term_memory
        self.preferences = user_preferences

    async def build_context(self, user_query: str) -> Dict[str, Any]:
        """Assembles unified memory context snapshot for reasoning and dialogue generation."""
        recent_messages = self.short_term.get_messages(limit=10)
        relevant_docs = await self.long_term.search(user_query, limit=3)
        working_state = self.working.snapshot()
        user_prefs = self.preferences.get_all()

        return {
            "conversation_history": recent_messages,
            "knowledge_docs": relevant_docs,
            "working_memory": working_state,
            "user_preferences": user_prefs,
        }


memory_manager = MemoryManager()
