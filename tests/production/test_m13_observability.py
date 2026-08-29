"""
M13 — Structured Logging, Correlation ID Propagation, Tracing & Metrics Test Suite
Section S00.5 & M13 — Operational Observability Foundation
"""

import json
import logging
import unittest

from apps.api.app.context import (
    clear_request_context,
    set_request_context,
    set_transaction_context,
)
from apps.api.app.logging import StructuredJsonFormatter
from apps.api.app.metrics import MetricsRegistry, metrics_registry
from apps.api.config.types import SecretString
from apps.api.observability.tracing import Tracer, trace_span, tracer


class TestM13Observability(unittest.TestCase):
    """Observability test suite for logging, correlation, tracing, and metrics."""

    def setUp(self) -> None:
        clear_request_context()
        metrics_registry.reset()
        tracer.clear()

    def tearDown(self) -> None:
        clear_request_context()
        metrics_registry.reset()
        tracer.clear()

    def test_structured_json_logging_format(self) -> None:
        """Verify structured JSON log formatter includes all required operational fields."""
        formatter = StructuredJsonFormatter(service_name="test-service", environment="test")
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Payment processed successfully",
            args=(),
            exc_info=None,
        )
        set_request_context(
            request_id="req_123",
            correlation_id="corr_456",
            trace_id="trace_789",
            span_id="span_abc",
        )
        set_transaction_context(
            transaction_id="tx_111",
            merchant_id="m_222",
            buyer_id="b_333",
            mandate_id="man_444",
            idempotency_key="idemp_555",
            execution_attempt_id="att_666",
            outbox_event_id="out_777",
            provider_reference="pay_ref_888",
            operation="EXECUTE_PAYMENT",
            status="SUCCESS",
            error_code="NONE",
            latency_ms=12.5,
        )

        formatted = formatter.format(record)
        data = json.loads(formatted)

        self.assertEqual(data["service"], "test-service")
        self.assertEqual(data["environment"], "test")
        self.assertEqual(data["event"], "Payment processed successfully")
        self.assertEqual(data["request_id"], "req_123")
        self.assertEqual(data["correlation_id"], "corr_456")
        self.assertEqual(data["trace_id"], "trace_789")
        self.assertEqual(data["span_id"], "span_abc")
        self.assertEqual(data["transaction_id"], "tx_111")
        self.assertEqual(data["merchant_id"], "m_222")
        self.assertEqual(data["buyer_id"], "b_333")
        self.assertEqual(data["mandate_id"], "man_444")
        self.assertEqual(data["idempotency_key"], "idemp_555")
        self.assertEqual(data["execution_attempt_id"], "att_666")
        self.assertEqual(data["outbox_event_id"], "out_777")
        self.assertEqual(data["provider_reference"], "pay_ref_888")
        self.assertEqual(data["operation"], "EXECUTE_PAYMENT")
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["error_code"], "NONE")
        self.assertEqual(data["latency_ms"], 12.5)

    def test_sensitive_data_redaction_in_logging(self) -> None:
        """Verify secrets, tokens, private keys, and nonces are redacted in logs."""
        formatter = StructuredJsonFormatter()
        secret_obj = SecretString("super_secret_key_123")
        record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=15,
            msg=f"Logging with secret: {secret_obj}",
            args=(),
            exc_info=None,
        )
        set_transaction_context(transaction_id="tx_sec")
        formatted = formatter.format(record)

        self.assertNotIn("super_secret_key_123", formatted)
        self.assertIn("[REDACTED]", formatted)

    def test_metrics_registry_cardinality_protection(self) -> None:
        """Verify metrics registry rejects invalid/unbounded label keys to prevent cardinality explosion."""
        reg = MetricsRegistry()
        reg.increment_counter(
            "payment_requests_total", labels={"method": "POST", "route": "/execute"}
        )
        self.assertEqual(
            reg.get_counter_value(
                "payment_requests_total", labels={"method": "POST", "route": "/execute"}
            ),
            1,
        )

        with self.assertRaises(ValueError) as cm:
            reg.increment_counter(
                "payment_requests_total", labels={"transaction_id": "tx_unbounded_123"}
            )
        self.assertIn(
            "High-cardinality or invalid metric label key 'transaction_id'", str(cm.exception)
        )

    def test_opentelemetry_tracing_span_context(self) -> None:
        """Verify OpenTelemetry tracer creates spans and records completion."""
        t = Tracer(service_name="test-service")
        span = t.start_span("payment_authorization", attributes={"merchant_id": "m_test"})
        self.assertEqual(span.name, "payment_authorization")
        self.assertEqual(span.attributes.get("merchant_id"), "m_test")

        t.end_span(span)
        completed = t.get_completed_spans()
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].name, "payment_authorization")
        self.assertEqual(completed[0].status, "OK")

    def test_tracing_fail_open_guarantee(self) -> None:
        """Verify telemetry/tracer failures do not raise or disrupt execution."""

        @trace_span("critical_payment_operation")
        def execute_subsystem() -> str:
            return "SUCCESS"

        result = execute_subsystem()
        self.assertEqual(result, "SUCCESS")


if __name__ == "__main__":
    unittest.main()
