"""
Telemetry and Performance Metrics Subsystem for T AI Operating System.
Tracks system counters, latency, memory usage, and execution telemetry.
"""

import time
from typing import Dict, Any, List
from brain.logging.logger import get_logger

log = get_logger("telemetry")


class MetricsCollector:
    """Collects and reports system performance telemetry metrics."""
    
    def __init__(self) -> None:
        self._counters: Dict[str, int] = {}
        self._latencies: Dict[str, List[float]] = {}
        self._start_time: float = time.time()

    def increment(self, metric: str, value: int = 1) -> None:
        """Increments a numerical counter metric."""
        self._counters[metric] = self._counters.get(metric, 0) + value

    def record_latency(self, metric: str, duration_seconds: float) -> None:
        """Records an execution latency sample."""
        if metric not in self._latencies:
            self._latencies[metric] = []
        self._latencies[metric].append(duration_seconds)
        # Keep sliding window of 100 samples
        if len(self._latencies[metric]) > 100:
            self._latencies[metric].pop(0)

    def get_summary(self) -> Dict[str, Any]:
        """Returns a snapshot summary of system telemetry metrics."""
        avg_latencies: Dict[str, float] = {}
        for k, v in self._latencies.items():
            avg_latencies[k] = round(sum(v) / len(v), 4) if v else 0.0

        return {
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "counters": self._counters.copy(),
            "avg_latencies_sec": avg_latencies,
        }


metrics = MetricsCollector()
