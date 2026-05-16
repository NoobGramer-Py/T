"""
Session logger for T's red team lab.
Records every step, finding, and result for the auto-generated report.
"""

import time
from dataclasses import dataclass, field
from typing import Literal

StepStatus = Literal["pending", "running", "done", "failed", "skipped"]


@dataclass
class LogEntry:
    ts:          float
    step:        str
    action:      str
    result:      str
    severity:    Literal["info", "low", "medium", "high", "critical"] = "info"
    evidence:    str = ""


@dataclass
class LabSession:
    start_ts:    float = field(default_factory=time.time)
    end_ts:      float = 0.0
    target_ip:   str   = ""
    devices:     list  = field(default_factory=list)
    findings:    list  = field(default_factory=list)
    creds:       list  = field(default_factory=list)
    data_accessed: list = field(default_factory=list)
    log:         list[LogEntry] = field(default_factory=list)
    active:      bool  = False

    def record(self, step: str, action: str, result: str,
               severity: str = "info", evidence: str = "") -> None:
        self.log.append(LogEntry(
            ts=time.time(), step=step, action=action,
            result=result, severity=severity, evidence=evidence,
        ))

    def add_finding(self, title: str, severity: str, device: str,
                    description: str, remediation: str = "") -> None:
        self.findings.append({
            "title": title, "severity": severity, "device": device,
            "description": description, "remediation": remediation,
            "ts": time.time(),
        })

    def add_cred(self, source: str, username: str, password: str, extra: str = "") -> None:
        self.creds.append({
            "source": source, "username": username,
            "password": password, "extra": extra, "ts": time.time(),
        })

    def add_device(self, ip: str, mac: str, hostname: str,
                   os_hint: str, open_ports: list, device_type: str) -> None:
        # Deduplicate by IP
        existing = next((d for d in self.devices if d["ip"] == ip), None)
        if existing:
            existing.update({"mac": mac, "hostname": hostname,
                             "os_hint": os_hint, "open_ports": open_ports,
                             "device_type": device_type})
        else:
            self.devices.append({
                "ip": ip, "mac": mac, "hostname": hostname,
                "os_hint": os_hint, "open_ports": open_ports,
                "device_type": device_type, "ts": time.time(),
            })

    def add_data(self, device: str, data_type: str, size: str, path: str = "") -> None:
        self.data_accessed.append({
            "device": device, "data_type": data_type,
            "size": size, "path": path, "ts": time.time(),
        })

    def finish(self) -> None:
        self.end_ts = time.time()
        self.active = False

    def duration_str(self) -> str:
        end = self.end_ts or time.time()
        secs = int(end - self.start_ts)
        return f"{secs // 3600}h {(secs % 3600) // 60}m {secs % 60}s"


# Module-level current session
current: LabSession = LabSession()


def start_session(target_ip: str = "") -> LabSession:
    global current
    current = LabSession(target_ip=target_ip, active=True)
    return current


def get_session() -> LabSession:
    return current
