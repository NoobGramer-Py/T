"""
System health monitor for T's proactive engine.
Uses psutil for lightweight polling (every 30s).
Returns structured anomalies when thresholds are crossed.
"""

import psutil
from dataclasses import dataclass
from core.logger import get_logger

log = get_logger("proactive.monitor")

# Thresholds
_CPU_WARN_PCT    = 85.0
_RAM_WARN_PCT    = 90.0
_DISK_WARN_GB    = 5.0
_CONSEC_CPU_HITS = 2   # consecutive checks required before firing

# Ports that are suspicious when they appear unexpectedly
_SUSPICIOUS_PORTS = {4444, 4445, 5555, 9001, 1337, 31337, 6666, 6667}

# User-visible processes worth tracking for crash detection
_WATCHED_PROCS = {
    "chrome.exe", "firefox.exe", "msedge.exe",
    "code.exe",   "discord.exe", "steam.exe",
}


@dataclass
class Anomaly:
    kind:     str   # "cpu" | "ram" | "disk" | "new_port" | "process_gone"
    message:  str
    severity: str   # "info" | "warn" | "critical"


class SystemMonitor:
    def __init__(self) -> None:
        self._cpu_hits:        int       = 0
        self._known_ports:     set[int]  = set()
        self._known_processes: set[str]  = set()
        self._initialized:     bool      = False

    def check(self) -> list[Anomaly]:
        """
        Run one poll cycle.
        Returns a list of Anomaly objects for any thresholds crossed.
        Safe to call on non-Windows — psutil is cross-platform.
        """
        anomalies: list[Anomaly] = []
        self._check_cpu(anomalies)
        self._check_ram(anomalies)
        self._check_disk(anomalies)
        self._check_ports(anomalies)
        self._check_processes(anomalies)
        self._initialized = True
        return anomalies

    # ── CPU ──────────────────────────────────────────────────────────────────

    def _check_cpu(self, out: list[Anomaly]) -> None:
        try:
            pct = psutil.cpu_percent(interval=1)
            if pct >= _CPU_WARN_PCT:
                self._cpu_hits += 1
                if self._cpu_hits >= _CONSEC_CPU_HITS:
                    out.append(Anomaly(
                        kind="cpu",
                        message=f"CPU at {pct:.0f}% — {self._top_cpu_proc()}",
                        severity="warn",
                    ))
            else:
                self._cpu_hits = 0
        except Exception as e:
            log.debug(f"cpu check error: {e}")

    # ── RAM ──────────────────────────────────────────────────────────────────

    def _check_ram(self, out: list[Anomaly]) -> None:
        try:
            mem = psutil.virtual_memory()
            if mem.percent >= _RAM_WARN_PCT:
                out.append(Anomaly(
                    kind="ram",
                    message=f"RAM at {mem.percent:.0f}% — {self._top_ram_proc()}",
                    severity="warn",
                ))
        except Exception as e:
            log.debug(f"ram check error: {e}")

    # ── Disk ─────────────────────────────────────────────────────────────────

    def _check_disk(self, out: list[Anomaly]) -> None:
        try:
            for part in psutil.disk_partitions(all=False):
                try:
                    usage  = psutil.disk_usage(part.mountpoint)
                    free_g = usage.free / (1024 ** 3)
                    if free_g < _DISK_WARN_GB:
                        out.append(Anomaly(
                            kind="disk",
                            message=f"Low disk on {part.mountpoint}: {free_g:.1f} GB free",
                            severity="critical" if free_g < 1 else "warn",
                        ))
                except PermissionError:
                    pass
        except Exception as e:
            log.debug(f"disk check error: {e}")

    # ── Network ports ────────────────────────────────────────────────────────

    def _check_ports(self, out: list[Anomaly]) -> None:
        try:
            current: set[int] = set()
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "LISTEN":
                    current.add(conn.laddr.port)

            if self._initialized:
                for port in current - self._known_ports:
                    proc = self._proc_for_port(port)
                    sev  = "critical" if port in _SUSPICIOUS_PORTS else "warn"
                    out.append(Anomaly(
                        kind="new_port",
                        message=f"New listening port {port} — {proc}",
                        severity=sev,
                    ))

            self._known_ports = current
        except Exception as e:
            log.debug(f"port check error: {e}")

    # ── Process crash ────────────────────────────────────────────────────────

    def _check_processes(self, out: list[Anomaly]) -> None:
        try:
            current = {p.name().lower() for p in psutil.process_iter(["name"])}
            if self._initialized:
                for name in self._known_processes - current:
                    out.append(Anomaly(
                        kind="process_gone",
                        message=f"Process disappeared: {name}",
                        severity="info",
                    ))
            self._known_processes = current & _WATCHED_PROCS
        except Exception as e:
            log.debug(f"process check error: {e}")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _top_cpu_proc(self) -> str:
        try:
            procs = sorted(
                psutil.process_iter(["name", "cpu_percent"]),
                key=lambda p: p.info["cpu_percent"] or 0,
                reverse=True,
            )
            if procs:
                p = procs[0]
                return f"{p.info['name']} at {p.info['cpu_percent']:.0f}% CPU"
        except Exception:
            pass
        return "unknown process"

    def _top_ram_proc(self) -> str:
        try:
            procs = sorted(
                psutil.process_iter(["name", "memory_info"]),
                key=lambda p: (p.info["memory_info"] or type("o", (), {"rss": 0})()).rss,
                reverse=True,
            )
            if procs and procs[0].info["memory_info"]:
                p  = procs[0]
                mb = p.info["memory_info"].rss / (1024 ** 2)
                return f"{p.info['name']} consuming {mb:.0f} MB"
        except Exception:
            pass
        return "unknown process"

    def _proc_for_port(self, port: int) -> str:
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "LISTEN" and conn.laddr.port == port and conn.pid:
                    return f"{psutil.Process(conn.pid).name()} (PID {conn.pid})"
        except Exception:
            pass
        return "unknown process"
