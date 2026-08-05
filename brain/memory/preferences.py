"""
User Preferences & Personality Constraints Store for T AI OS.
Maintains explicitly authorized user preferences, habits, and system defaults.
"""

from typing import Dict, Any, Optional


class UserPreferencesStore:
    """Manages user-defined preferences and operational guidelines."""

    def __init__(self) -> None:
        self._preferences: Dict[str, Any] = {
            "theme": "dark",
            "voice_enabled": False,
            "auto_execution": False,
            "preferred_model": "llama-3.3-70b-versatile",
        }

    def set_preference(self, key: str, value: Any) -> None:
        """Sets a user preference item."""
        self._preferences[key] = value

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Retrieves a user preference item."""
        return self._preferences.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """Returns snapshot of all stored user preferences."""
        return self._preferences.copy()


user_preferences = UserPreferencesStore()
