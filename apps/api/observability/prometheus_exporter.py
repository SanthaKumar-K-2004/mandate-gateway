"""
Mandate Gateway — Prometheus Metrics Instrumentation Exporter (M29)
Workstream 3 — Collects and formats Prometheus operational metrics for API, AI Agent, Commerce, and Payment Safety.
Strictly excludes sensitive tokens, raw payment credentials, and prompts from metric labels.
"""

from __future__ import annotations

import logging
import threading
from typing import Dict

logger = logging.getLogger("mandate_gateway.prometheus_exporter")


class PrometheusMetricsRegistry:
    """Thread-safe Prometheus metrics registry for Mandate Gateway runtime."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> PrometheusMetricsRegistry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_metrics()
            return cls._instance

    def _init_metrics(self) -> None:
        self._lock = threading.Lock()

        # API Metrics
        self.http_requests_total: Dict[str, int] = {}
        self.http_errors_total: Dict[str, int] = {}

        # AI Agent Metrics
        self.ai_agent_requests_total: int = 0
        self.ai_agent_research_ops_total: int = 0
        self.ai_agent_rejected_ops_total: int = 0
        self.ai_agent_provider_failures_total: int = 0
        self.ai_agent_product_truth_failures_total: int = 0
        self.ai_agent_llm_failures_total: int = 0

        # Commerce Metrics
        self.commerce_connector_requests_total: Dict[str, int] = {}
        self.commerce_connector_failures_total: Dict[str, int] = {}
        self.commerce_circuit_breaker_state: Dict[str, int] = {}  # 0=CLOSED, 1=OPEN, 2=HALF_OPEN
        self.commerce_reconciliation_backlog_count: int = 0

        # Payment Safety Metrics
        self.payment_confirmation_attempts_total: int = 0
        self.payment_duplicate_rejections_total: int = 0
        self.payment_idempotency_conflicts_total: int = 0
        self.payment_order_mismatch_rejections_total: int = 0

    def record_http_request(self, method: str, endpoint: str, status_code: int) -> None:
        """Record API request count."""
        with self._lock:
            key = f"{method}:{endpoint}:{status_code}"
            self.http_requests_total[key] = self.http_requests_total.get(key, 0) + 1
            if status_code >= 400:
                self.http_errors_total[key] = self.http_errors_total.get(key, 0) + 1

    def record_ai_agent_event(self, event_type: str) -> None:
        """Record AI Agent operation metrics."""
        with self._lock:
            self.ai_agent_requests_total += 1
            if event_type == "research":
                self.ai_agent_research_ops_total += 1
            elif event_type == "rejected":
                self.ai_agent_rejected_ops_total += 1
            elif event_type == "provider_failure":
                self.ai_agent_provider_failures_total += 1
            elif event_type == "product_truth_failure":
                self.ai_agent_product_truth_failures_total += 1
            elif event_type == "llm_failure":
                self.ai_agent_llm_failures_total += 1

    def record_connector_request(self, connector_id: str, success: bool) -> None:
        """Record commerce connector request metrics."""
        with self._lock:
            self.commerce_connector_requests_total[connector_id] = (
                self.commerce_connector_requests_total.get(connector_id, 0) + 1
            )
            if not success:
                self.commerce_connector_failures_total[connector_id] = (
                    self.commerce_connector_failures_total.get(connector_id, 0) + 1
                )

    def record_payment_safety_event(self, event_type: str) -> None:
        """Record payment safety enforcement metric."""
        with self._lock:
            if event_type == "confirmation_attempt":
                self.payment_confirmation_attempts_total += 1
            elif event_type == "duplicate_rejection":
                self.payment_duplicate_rejections_total += 1
            elif event_type == "idempotency_conflict":
                self.payment_idempotency_conflicts_total += 1
            elif event_type == "order_mismatch_rejection":
                self.payment_order_mismatch_rejections_total += 1

    def generate_prometheus_text(self) -> str:
        """Generate Prometheus exposition text format."""
        lines = []

        # API Metrics
        lines.append("# HELP http_requests_total Total count of HTTP requests processed")
        lines.append("# TYPE http_requests_total counter")
        for key, val in self.http_requests_total.items():
            method, endpoint, status_code = key.split(":")
            lines.append(
                f'http_requests_total{{method="{method}",endpoint="{endpoint}",status="{status_code}"}} {val}'
            )

        # AI Agent Metrics
        lines.append("# HELP ai_agent_requests_total Total count of AI Agent operations")
        lines.append("# TYPE ai_agent_requests_total counter")
        lines.append(f"ai_agent_requests_total {self.ai_agent_requests_total}")
        lines.append(f"ai_agent_research_ops_total {self.ai_agent_research_ops_total}")
        lines.append(f"ai_agent_rejected_ops_total {self.ai_agent_rejected_ops_total}")

        # Commerce Metrics
        lines.append(
            "# HELP commerce_connector_requests_total Total count of commerce connector calls"
        )
        lines.append("# TYPE commerce_connector_requests_total counter")
        for cid, val in self.commerce_connector_requests_total.items():
            lines.append(f'commerce_connector_requests_total{{connector="{cid}"}} {val}')

        # Payment Safety Metrics
        lines.append(
            "# HELP payment_confirmation_attempts_total Total payment confirmation attempts"
        )
        lines.append("# TYPE payment_confirmation_attempts_total counter")
        lines.append(
            f"payment_confirmation_attempts_total {self.payment_confirmation_attempts_total}"
        )
        lines.append(
            f"payment_duplicate_rejections_total {self.payment_duplicate_rejections_total}"
        )
        lines.append(
            f"payment_idempotency_conflicts_total {self.payment_idempotency_conflicts_total}"
        )
        lines.append(
            f"payment_order_mismatch_rejections_total {self.payment_order_mismatch_rejections_total}"
        )

        return "\n".join(lines) + "\n"
