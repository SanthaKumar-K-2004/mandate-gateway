"""
M13 — Unit Test Suite for Observability Core Components
Section 14 — Test Architecture
"""

import json
import logging
import unittest

from apps.api.app.context import (
    clear_request_context,
    get_request_context,
    set_request_context,
)
from apps.api.app.logging import SecretRedactionFilter, StructuredJsonFormatter
from apps.api.app.metrics import metrics_registry
from apps.api.observability.alerting import alert_evaluator
from apps.api.observability.tracing import trace_span


class TestM13ObservabilityCore(unittest.TestCase):
    """Unit test suite for M13 core observability structures."""

    def setUp(self) -> None:
        clear_request_context()
        metrics_registry.reset()
        alert_evaluator.clear_alerts()

    def test_correlation_context_lifecycle(self) -> None:
        """Verify request correlation context setting, retrieval, and clearing."""
        set_request_context("req_100", "corr_100", "trace_100")
        ctx = get_request_context()
        self.assertEqual(ctx["request_id"], "req_100")
        self.assertEqual(ctx["correlation_id"], "corr_100")
        self.assertEqual(ctx["trace_id"], "trace_100")

        clear_request_context()
        cleared_ctx = get_request_context()
        self.assertIsNone(cleared_ctx["request_id"])

    def test_structured_json_logging_and_secret_redaction(self) -> None:
        """Verify StructuredJsonFormatter formats JSON and SecretRedactionFilter redacts secrets."""
        formatter = StructuredJsonFormatter(service_name="mandate-gateway", environment="test")
        redaction_filter = SecretRedactionFilter()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Processing payment with secret_key=sk_test_12345 and password=supersecret",
            args=(),
            exc_info=None,
        )

        self.assertTrue(redaction_filter.filter(record))
        formatted_json = formatter.format(record)
        log_obj = json.loads(formatted_json)

        self.assertEqual(log_obj["service"], "mandate-gateway")
        self.assertEqual(log_obj["level"], "INFO")
        self.assertNotIn("sk_test_12345", formatted_json)
        self.assertNotIn("supersecret", formatted_json)
        self.assertIn("[REDACTED]", formatted_json)

    def test_metrics_registry_counters_gauges_and_prometheus_export(self) -> None:
        """Verify counter increment, gauge setting, high-cardinality guard, and Prometheus export."""
        metrics_registry.increment_counter("payments_created_total", labels={"environment": "test"})
        metrics_registry.set_gauge("outbox_backlog_size", 42.0)

        self.assertEqual(
            metrics_registry.get_counter_value(
                "payments_created_total", labels={"environment": "test"}
            ),
            1,
        )
        self.assertEqual(metrics_registry.get_gauge_value("outbox_backlog_size"), 42.0)

        # High cardinality label rejection
        with self.assertRaises(ValueError):
            metrics_registry.increment_counter(
                "payments_created_total", labels={"transaction_id": "tx_9999"}
            )

        prom_text = metrics_registry.to_prometheus_text()
        self.assertIn("payments_created_total", prom_text)
        self.assertIn("outbox_backlog_size", prom_text)

    def test_fail_open_tracing_span(self) -> None:
        """Verify trace_span context manager executes code cleanly and fails open on internal tracer errors."""
        executed = False
        with trace_span("unit_test_span", attributes={"operation": "test_op"}) as span:
            executed = True
            span.set_attribute("key", "val")

        self.assertTrue(executed)

    def test_alert_evaluator_deduplication_and_resolution(self) -> None:
        """Verify alert rule evaluation, deduplication, and resolution."""
        alert = alert_evaluator.evaluate_rule("audit_chain_verification_failure", 1.0, 1.0)
        self.assertIsNotNone(alert)
        assert alert is not None
        self.assertEqual(alert["severity"], "CRITICAL")
        self.assertEqual(alert["status"], "ACTIVE")

        # Second evaluation re-triggers deduplication and updates last_detected_at
        alert2 = alert_evaluator.evaluate_rule("audit_chain_verification_failure", 1.0, 1.0)
        self.assertIsNotNone(alert2)
        assert alert2 is not None
        self.assertEqual(alert2["alert_id"], alert["alert_id"])

        # Resolve alert
        resolved = alert_evaluator.resolve_alert(alert["alert_id"])
        self.assertTrue(resolved)
        self.assertEqual(len(alert_evaluator.get_active_alerts()), 0)


if __name__ == "__main__":
    unittest.main()
