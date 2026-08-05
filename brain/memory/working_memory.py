"""
Working Memory Layer for T AI OS.
Maintains active scratchpad state, temporary parameters, and dynamic variables for executing tasks.
"""

from typing import Dict, Any, Optional


class WorkingMemory:
    """Manages active scratchpad variables during complex reasoning & execution."""

    def __init__(self) -> None:
        self._scratchpad: Dict[str, Any] = {}

    def set_variable(self, key: str, value: Any) -> None:
        """Sets a transient variable in working memory."""
        self._scratchpad[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Retrieves a variable from working memory."""
        return self._scratchpad.get(key, default)

    def clear(self) -> None:
        """Clears all working memory state."""
        self._scratchpad.clear()

    def snapshot(self) -> Dict[str, Any]:
        """Returns snapshot of working memory."""
        return self._scratchpad.copy()


working_memory = WorkingMemory()
