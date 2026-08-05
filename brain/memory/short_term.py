"""
Short-Term Conversation Memory Layer for T AI OS.
Maintains transient conversation history and sliding context window buffers.
"""

from typing import List, Dict, Any


class ShortTermMemory:
    """Manages active dialogue context buffer for live sessions."""

    def __init__(self, max_messages: int = 50) -> None:
        self.max_messages = max_messages
        self._history: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str) -> None:
        """Adds a message to short-term history buffer."""
        self._history.append({"role": role, "content": content})
        if len(self._history) > self.max_messages:
            self._history.pop(0)

    def get_messages(self, limit: int = 20) -> List[Dict[str, str]]:
        """Retrieves recent conversation messages."""
        return self._history[-limit:]

    def clear(self) -> None:
        """Clears short-term conversation context."""
        self._history.clear()


short_term_memory = ShortTermMemory()
