"""
Target session manager for T's real-world offensive operations.
Manages scope: IPs, domains, bug bounty programs, CTF boxes.
Every action confirms target is in-scope before executing.
"""

import time
from dataclasses import dataclass, field
from typing import Literal
from core.logger import get_logger

log = get_logger("offensive.target_session")

TargetType = Literal["ip", "domain", "bugbounty", "ctf", "custom"]


@dataclass
class Target:
    id:          str
    type:        TargetType
    value:       str            # IP, domain, or program name
    scope_notes: str = ""       # what is/isn't in scope
    program_url: str = ""       # HackerOne/Bugcrowd URL
    added_ts:    float = field(default_factory=time.time)
    authorized:  bool = True    # always true — user only adds their own targets


@dataclass
class OperationSession:
    id:        str
    name:      str
    targets:   list[Target]     = field(default_factory=list)
    notes:     str              = ""
    started:   float            = field(default_factory=time.time)
    active:    bool             = True
    findings:  list[dict]       = field(default_factory=list)
    log:       list[dict]       = field(default_factory=list)

    def add_target(self, target: Target) -> None:
        if not any(t.value == target.value for t in self.targets):
            self.targets.append(target)
            log.info(f"target added: {target.value} ({target.type})")

    def remove_target(self, target_id: str) -> bool:
        before = len(self.targets)
        self.targets = [t for t in self.targets if t.id != target_id]
        return len(self.targets) < before

    def in_scope(self, value: str) -> bool:
        """Check if a value (IP/domain) is in the current scope."""
        value = value.lower().strip()
        for t in self.targets:
            tv = t.value.lower().strip()
            # Exact match
            if value == tv:
                return True
            # Subnet match: 192.168.1 matches 192.168.1.0/24
            if tv.endswith("/24") and value.startswith(tv[:-3]):
                return True
            # Domain/subdomain match
            if value.endswith(f".{tv}") or value == tv:
                return True
        return False

    def record(self, action: str, target: str, result: str, severity: str = "info") -> None:
        self.log.append({
            "ts": time.time(), "action": action,
            "target": target, "result": result, "severity": severity,
        })

    def add_finding(self, title: str, severity: str, target: str,
                    description: str, cvss: float = 0.0) -> None:
        self.findings.append({
            "title": title, "severity": severity, "target": target,
            "description": description, "cvss": cvss, "ts": time.time(),
        })

    def to_dict(self) -> dict:
        return {
            "id":       self.id,
            "name":     self.name,
            "active":   self.active,
            "notes":    self.notes,
            "started":  self.started,
            "targets":  [
                {"id": t.id, "type": t.type, "value": t.value,
                 "scope_notes": t.scope_notes, "program_url": t.program_url}
                for t in self.targets
            ],
            "finding_count": len(self.findings),
            "log_count":     len(self.log),
        }


# ── Module-level session registry ──────────────────────────────────────────────

_sessions: dict[str, OperationSession] = {}
_active_id: str = ""


def create_session(name: str, notes: str = "") -> OperationSession:
    global _active_id
    import uuid
    sess = OperationSession(id=str(uuid.uuid4())[:8], name=name, notes=notes)
    _sessions[sess.id] = sess
    _active_id = sess.id
    log.info(f"operation session created: {name!r}")
    return sess


def get_active() -> OperationSession | None:
    return _sessions.get(_active_id)


def get_session(session_id: str) -> OperationSession | None:
    return _sessions.get(session_id)


def list_sessions() -> list[dict]:
    return [s.to_dict() for s in _sessions.values()]


def close_session(session_id: str) -> bool:
    sess = _sessions.get(session_id)
    if sess:
        sess.active = False
        return True
    return False


def add_target_to_active(target_type: str, value: str,
                          scope_notes: str = "", program_url: str = "") -> Target | None:
    import uuid
    sess = get_active()
    if not sess:
        # Auto-create a default session
        sess = create_session("Default Operation")
    t = Target(
        id=str(uuid.uuid4())[:8],
        type=target_type,  # type: ignore[arg-type]
        value=value,
        scope_notes=scope_notes,
        program_url=program_url,
    )
    sess.add_target(t)
    return t
