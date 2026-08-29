"""
M13 — Failure Engineering Test Suite for Observability Infrastructure
Section 12 & 14 — Failure Engineering Requirements
"""

import unittest
from unittest.mock import patch

from apps.api.app.metrics import metrics_registry
from apps.api.observability.alerting import alert_evaluator
from apps.api.observability.degradation import (
    evaluate_telemetry_resilience,
    handle_dependency_degradation,
)
from apps.api.observability.tracing import trace_span


class TestM13ObservabilityFailureEngineering(unittest.TestCase):
    """Failure engineering test suite verifying system behavior when telemetry subsystems fail."""

    def setUp(self) -> None:
        metrics_registry.reset()
        alert_evaluator.clear_alerts()

    def test_telemetry_failure_does_not_fail_business_transaction(self) -> None:
        """Verify telemetry failure does NOT crash or roll back business transaction execution (Fail-Open)."""
        business_executed = False

        # Execute business logic inside trace_span when tracer throws internal exception
        with patch(
            "apps.api.observability.tracing.tracer.start_span",
            side_effect=RuntimeError("Tracer sink down"),
        ):
            with trace_span("failing_telemetry_span") as span:
                business_executed = True
                span.set_attribute("business_state", "COMMITTED")

        self.assertTrue(business_executed)
        res = evaluate_telemetry_resilience()
        self.assertTrue(res["telemetry_failed_open"])

    def test_logging_and_metrics_failure_swallowed_in_degradation(self) -> None:
        """Verify metric collection failure does not raise exception in degradation matrix."""
        with patch.object(
            metrics_registry, "increment_counter", side_effect=Exception("Metrics DB disk full")
        ):
            res = handle_dependency_degradation(
                "telemetry", Exception("Telemetry connection lost"), "test_op"
            )
            self.assertFalse(res["fail_closed"])
            self.assertEqual(res["action"], "FAIL_OPEN_LOG_ONLY")

    def test_outbox_backlog_growth_triggers_alert(self) -> None:
        """Verify outbox backlog exceeding threshold triggers outbox_backlog_threshold alert."""
        backlog_count = 150
        alert = alert_evaluator.evaluate_rule(
            rule_name="outbox_backlog_threshold",
            metric_value=float(backlog_count),
            threshold=100.0,
        )
        self.assertIsNotNone(alert)
        assert alert is not None
        self.assertEqual(alert["severity"], "WARNING")


if __name__ == "__main__":
    unittest.main()
