"""
Working memory for T's autonomous execution engine.
Accumulates every finding across steps so the planner always has
full context when deciding what to do next.
"""

from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class Finding:
    step:     str
    tool:     str
    key:      str         # e.g. "open_ports", "credentials", "flag"
    value:    Any
    severity: str = "info"
    ts:       float = field(default_factory=time.time)


class WorkingMemory:
    """
    Accumulates all discoveries across an autonomous task session.
    The planner reads this before every LLM call so context is always fresh.
    """

    def __init__(self, goal: str, target: str, task_type: str) -> None:
        self.goal        = goal
        self.target      = target
        self.task_type   = task_type   # audit | osint | ctf | attack
        self.start_ts    = time.time()

        # Structured findings
        self.hosts:       list[str]           = []
        self.open_ports:  dict[str, list[int]] = {}   # host → [ports]
        self.services:    list[dict]           = []
        self.creds:       list[dict]           = []
        self.flags:       list[str]            = []
        self.vulns:       list[dict]           = []
        self.subdomains:  list[str]            = []
        self.emails:      list[str]            = []
        self.usernames:   list[str]            = []
        self.social_accounts: list[dict]       = []
        self.breach_hits: list[dict]           = []
        self.sessions:    list[str]            = []   # active meterpreter/shell sessions

        # Raw step history (condensed)
        self.steps:       list[dict]           = []   # {name, tool, status, summary}
        self.raw_outputs: dict[str, str]       = {}   # step_name → raw output (stored but not streamed)

        # Findings log
        self.findings:    list[Finding]        = []

    # ── Ingestion helpers ─────────────────────────────────────────────────────

    def add_step(self, name: str, tool: str, status: str, summary: str, raw: str = "") -> None:
        self.steps.append({
            "name": name, "tool": tool,
            "status": status, "summary": summary,
            "ts": time.time(),
        })
        if raw:
            self.raw_outputs[name] = raw

    def add_finding(self, step: str, tool: str, key: str,
                    value: Any, severity: str = "info") -> None:
        self.findings.append(Finding(step, tool, key, value, severity))

        # Also route to typed stores
        if key == "host":
            if value not in self.hosts:
                self.hosts.append(value)
        elif key == "open_ports":
            host = step.split(":")[0] if ":" in step else self.target
            self.open_ports.setdefault(host, [])
            ports = value if isinstance(value, list) else [value]
            for p in ports:
                if p not in self.open_ports[host]:
                    self.open_ports[host].append(p)
        elif key == "service":
            self.services.append(value if isinstance(value, dict) else {"desc": value})
        elif key == "credential":
            self.creds.append(value if isinstance(value, dict) else {"raw": value})
        elif key == "flag":
            if value not in self.flags:
                self.flags.append(value)
        elif key == "vuln":
            self.vulns.append(value if isinstance(value, dict) else {"desc": value})
        elif key == "subdomain":
            if value not in self.subdomains:
                self.subdomains.append(value)
        elif key == "email":
            if value not in self.emails:
                self.emails.append(value)
        elif key == "username":
            if value not in self.usernames:
                self.usernames.append(value)
        elif key == "social":
            self.social_accounts.append(value if isinstance(value, dict) else {"platform": value})
        elif key == "breach":
            self.breach_hits.append(value if isinstance(value, dict) else {"desc": value})
        elif key == "session":
            if value not in self.sessions:
                self.sessions.append(value)

    # ── Context builder ───────────────────────────────────────────────────────

    def to_context(self) -> str:
        """
        Serialise working memory into a compact LLM-readable context block.
        Injected before every planner call.
        """
        parts = [
            f"GOAL: {self.goal}",
            f"TARGET: {self.target}",
            f"TYPE: {self.task_type}",
            f"ELAPSED: {int(time.time() - self.start_ts)}s",
            f"STEPS DONE: {len(self.steps)}",
        ]

        if self.hosts:
            parts.append(f"DISCOVERED HOSTS: {', '.join(self.hosts[:20])}")
        if self.open_ports:
            for h, ports in list(self.open_ports.items())[:5]:
                parts.append(f"OPEN PORTS ({h}): {', '.join(str(p) for p in sorted(ports)[:20])}")
        if self.services:
            descs = [s.get("desc", str(s)) for s in self.services[:10]]
            parts.append(f"SERVICES: {'; '.join(descs)}")
        if self.subdomains:
            parts.append(f"SUBDOMAINS ({len(self.subdomains)}): {', '.join(self.subdomains[:15])}")
        if self.emails:
            parts.append(f"EMAILS: {', '.join(self.emails[:10])}")
        if self.usernames:
            parts.append(f"USERNAMES: {', '.join(self.usernames[:10])}")
        if self.social_accounts:
            platforms = [a.get("platform", str(a)) for a in self.social_accounts[:10]]
            parts.append(f"SOCIAL ACCOUNTS ({len(self.social_accounts)}): {', '.join(platforms)}")
        if self.breach_hits:
            parts.append(f"BREACH HITS: {len(self.breach_hits)}")
        if self.vulns:
            descs = [v.get("desc", str(v)) for v in self.vulns[:5]]
            parts.append(f"VULNERABILITIES: {'; '.join(descs)}")
        if self.creds:
            parts.append(f"CREDENTIALS FOUND: {len(self.creds)}")
        if self.sessions:
            parts.append(f"ACTIVE SESSIONS: {', '.join(self.sessions[:5])}")
        if self.flags:
            parts.append(f"FLAGS CAPTURED: {', '.join(self.flags)}")

        # Last 3 steps summary
        if self.steps:
            recent = self.steps[-3:]
            lines  = [f"  [{s['status'].upper()}] {s['name']}: {s['summary'][:120]}" for s in recent]
            parts.append("RECENT STEPS:\n" + "\n".join(lines))

        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "goal":      self.goal,
            "target":    self.target,
            "task_type": self.task_type,
            "elapsed":   int(time.time() - self.start_ts),
            "steps":     self.steps,
            "hosts":     self.hosts,
            "open_ports":self.open_ports,
            "creds":     len(self.creds),
            "flags":     self.flags,
            "vulns":     len(self.vulns),
            "subdomains":len(self.subdomains),
            "emails":    len(self.emails),
            "social":    len(self.social_accounts),
            "breach":    len(self.breach_hits),
            "sessions":  self.sessions,
        }
