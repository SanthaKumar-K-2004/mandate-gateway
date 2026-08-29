"""
Mandate Gateway — Metrics Foundation
Section S00.5 — Observability Foundation
"""

import threading
from typing import Any, Dict, List, Optional, Tuple

# Bounded metric label safety allowlist (strict cardinality protection)
ALLOWED_LABEL_KEYS = {
    "method",
    "route",
    "status_class",
    "error_type",
    "event_type",
    "aggregate_type",
    "status",
    "operation",
    "provider_status",
    "failure_category",
    "reason",
    "environment",
    "service",
    "decision",
}


class MetricsRegistry:
    """
    In-memory metrics collector for Mandate Gateway.
    Thread-safe, local-first metric collection with strict label cardinality guards.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], int] = {}
        self._gauges: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = {}
        self._latencies: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], List[float]] = {}

    def _validate_labels(self, labels: Dict[str, str]) -> Tuple[Tuple[str, str], ...]:
        """Enforces label key allowlist to prevent high-cardinality label pollution."""
        sanitized = []
        for k, v in sorted(labels.items()):
            if k not in ALLOWED_LABEL_KEYS:
                raise ValueError(
                    f"High-cardinality or invalid metric label key '{k}' is prohibited. "
                    f"Allowed keys: {ALLOWED_LABEL_KEYS}"
                )
            sanitized.append((k, str(v)))
        return tuple(sanitized)

    def increment_counter(
        self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increments a counter metric safely."""
        label_tuple = self._validate_labels(labels or {})
        key = (name, label_tuple)

        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Sets a gauge metric value safely."""
        label_tuple = self._validate_labels(labels or {})
        key = (name, label_tuple)

        with self._lock:
            self._gauges[key] = float(value)

    def record_latency(
        self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Records request processing latency in milliseconds."""
        label_tuple = self._validate_labels(labels or {})
        key = (name, label_tuple)

        with self._lock:
            if key not in self._latencies:
                self._latencies[key] = []
            self._latencies[key].append(duration_ms)

    def get_counter_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> int:
        """Returns current counter value for given name and labels."""
        label_tuple = self._validate_labels(labels or {})
        key = (name, label_tuple)
        with self._lock:
            return self._counters.get(key, 0)

    def get_gauge_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Returns current gauge value for given name and labels."""
        label_tuple = self._validate_labels(labels or {})
        key = (name, label_tuple)
        with self._lock:
            return self._gauges.get(key, 0.0)

    def get_latencies(self, name: str, labels: Optional[Dict[str, str]] = None) -> List[float]:
        """Returns recorded latency values for given name and labels."""
        label_tuple = self._validate_labels(labels or {})
        key = (name, label_tuple)
        with self._lock:
            return list(self._latencies.get(key, []))

    def reset(self) -> None:
        """Resets all metrics (for test isolation)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._latencies.clear()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Returns structured summary of all counters, gauges, and latencies."""
        with self._lock:
            counters_out = {
                f"{k[0]}{{{','.join(f'{lk}=\"{lv}\"' for lk, lv in k[1])}}}": v
                for k, v in self._counters.items()
            }
            gauges_out = {
                f"{k[0]}{{{','.join(f'{lk}=\"{lv}\"' for lk, lv in k[1])}}}": v
                for k, v in self._gauges.items()
            }
            return {
                "counters": counters_out,
                "gauges": gauges_out,
            }

    def to_prometheus_text(self) -> str:
        """Formats collected metrics as Prometheus text representation."""
        lines = []
        with self._lock:
            for (name, labels), val in sorted(self._counters.items(), key=lambda x: x[0][0]):
                label_str = "{" + ",".join(f'{k}="{v}"' for k, v in labels) + "}" if labels else ""
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name}{label_str} {val}")
            for (name, labels), g_val in sorted(self._gauges.items(), key=lambda x: x[0][0]):
                label_str = "{" + ",".join(f'{k}="{v}"' for k, v in labels) + "}" if labels else ""
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name}{label_str} {g_val}")
        return "\n".join(lines) + "\n" if lines else "# No metrics recorded.\n"


# Global singleton metrics registry
metrics_registry = MetricsRegistry()
