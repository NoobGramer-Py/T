"""
Permission Manager and RBAC Policy Enforcement Subsystem.
Strictly enforces user authorization for sensitive actions, system operations, and execution tools.
"""

from typing import Dict, Any, Optional
from brain.config.config import config
from brain.security.audit import audit_logger
from brain.logging.logger import get_logger

log = get_logger("security.permissions")


class PermissionManager:
    """Evaluates and enforces permission policies across T OS."""

    def __init__(self) -> None:
        self.allowed_tools = set(config.security.allowed_execution_tools)
        self.require_confirmation = config.security.require_user_confirmation

    def is_action_allowed(self, action_type: str, resource: str, user_authorized: bool = False) -> bool:
        """
        Determines whether a specified action is permitted under current policies.
        User-authorized actions bypass confirmation if explicitly granted.
        """
        if config.security.sandbox_mode and action_type in ["terminal_command", "file_write"]:
            log.warning(f"Action '{action_type}' denied due to active Sandbox Mode.")
            audit_logger.log_event(action_type, resource, False, {"reason": "sandbox_mode_active"})
            return False

        if action_type not in self.allowed_tools:
            log.warning(f"Action '{action_type}' is not in allowed tools list.")
            audit_logger.log_event(action_type, resource, False, {"reason": "tool_not_whitelisted"})
            return False

        if self.require_confirmation and not user_authorized:
            log.info(f"Action '{action_type}' requires explicit user confirmation.")
            audit_logger.log_event(action_type, resource, False, {"reason": "awaiting_user_confirmation"})
            return False

        audit_logger.log_event(action_type, resource, True, {"reason": "authorized"})
        return True


permission_manager = PermissionManager()
