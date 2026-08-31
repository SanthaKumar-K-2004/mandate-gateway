"""
Mandate Gateway — Commerce Connector Health Monitor (M25)
Workstream 4 — Real-time health, latency, success rate, and error rate monitoring for commerce connectors.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


class CommerceConnectorHealthMonitor:
    """Real-time Health, Latency, and Error Rate Monitor for Commerce Connectors."""

    def __init__(self) -> None:
        self._metrics: Dict[str, Dict[str, Any]] = {
            "connector_cafe_acme_api": {
                "name": "Cafe Acme Specialty Coffee (Direct API)",
                "status": "HEALTHY",
                "latency_ms": 210,
                "success_count": 142,
                "failure_count": 1,
                "rate_limit_count": 0,
                "webhook_failures": 0,
                "success_rate_pct": 99.3,
                "last_checked": datetime.now(timezone.utc).isoformat(),
            },
            "connector_generic_web": {
                "name": "Generic Web Checkout Handoff",
                "status": "HEALTHY",
                "latency_ms": 80,
                "success_count": 310,
                "failure_count": 0,
                "rate_limit_count": 0,
                "webhook_failures": 0,
                "success_rate_pct": 100.0,
                "last_checked": datetime.now(timezone.utc).isoformat(),
            },
            "live_data_orchestrator": {
                "name": "Live Search Product Discovery (Tavily/Brave)",
                "status": "HEALTHY",
                "latency_ms": 450,
                "success_count": 98,
                "failure_count": 2,
                "rate_limit_count": 0,
                "webhook_failures": 0,
                "success_rate_pct": 98.0,
                "last_checked": datetime.now(timezone.utc).isoformat(),
            },
        }

    def record_call(
        self, connector_id: str, duration_ms: float, is_success: bool, is_rate_limit: bool = False
    ) -> None:
        """Record an API invocation event for health metrics tracking."""
        if connector_id not in self._metrics:
            self._metrics[connector_id] = {
                "name": f"Connector ({connector_id})",
                "status": "HEALTHY",
                "latency_ms": int(duration_ms),
                "success_count": 0,
                "failure_count": 0,
                "rate_limit_count": 0,
                "webhook_failures": 0,
                "success_rate_pct": 100.0,
                "last_checked": datetime.now(timezone.utc).isoformat(),
            }

        data = self._metrics[connector_id]
        if is_success:
            data["success_count"] += 1
        else:
            data["failure_count"] += 1

        if is_rate_limit:
            data["rate_limit_count"] += 1

        # Smooth latency calculation
        data["latency_ms"] = int(0.8 * data["latency_ms"] + 0.2 * duration_ms)
        total = data["success_count"] + data["failure_count"]
        data["success_rate_pct"] = (
            round((data["success_count"] / total) * 100.0, 1) if total > 0 else 100.0
        )

        if data["success_rate_pct"] < 90.0 or data["rate_limit_count"] > 5:
            data["status"] = "DEGRADED"
        elif data["success_rate_pct"] < 70.0:
            data["status"] = "UNAVAILABLE"
        else:
            data["status"] = "HEALTHY"

        data["last_checked"] = datetime.now(timezone.utc).isoformat()

    def record_webhook_failure(self, connector_id: str = "connector_cafe_acme_api") -> None:
        """Record a webhook verification failure."""
        if connector_id in self._metrics:
            self._metrics[connector_id]["webhook_failures"] += 1

    def get_health_metrics(self) -> Dict[str, Any]:
        """Fetch health metrics for all monitored connectors."""
        return {
            "status": "SUCCESS",
            "connectors": self._metrics,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
