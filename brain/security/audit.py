"""
Security Audit Logger for T AI Operating System.
Maintains an audit trail of user authorizations, execution events, and security policy checks.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict
from brain.config.config import config
from brain.logging.logger import get_logger

log = get_logger("security.audit")


class AuditLogger:
    """Logs security audit records to a structured JSON file."""

    def __init__(self) -> None:
        self.log_path = Path(config.security.audit_log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(self, action: str, subject: str, authorized: bool, details: Dict[str, Any]) -> None:
        """Records an authorized or denied security action."""
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": action,
            "subject": subject,
            "authorized": authorized,
            "details": details,
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            log.error(f"Failed writing audit log: {e}")


audit_logger = AuditLogger()
