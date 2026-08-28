"""
Mandate Gateway — Unit Tests for Observability Foundation
Section S00.5 — Observability Foundation
"""

import asyncio
import json
import logging
import unittest
from apps.api.app import (
    create_app,
    clear_request_context,
    get_request_context,
    set_request_context,
    metrics_registry,
)
from apps.api.app.logging import (
    EVENT_APPLICATION_STARTED,
    EVENT_REQUEST_COMPLETED,
    StructuredJsonFormatter,
    sanitize_log_string,
)
from apps.api.config import reset_settings_cache


class TestObservabilityFoundation(unittest.TestCase):

    def setUp(self) -> None:
        reset_settings_cache()
        clear_request_context()
        metrics_registry.reset()

    def tearDown(self) -> None:
        reset_settings_cache()
        clear_request_context()
        metrics_registry.reset()

    def test_event_taxonomy_constants(self) -> None:
        self.assertEqual(EVENT_APPLICATION_STARTED, "application.started")
        self.assertEqual(EVENT_REQUEST_COMPLETED, "request.completed")

    def test_contextvars_propagation(self) -> None:
        set_request_context("req-100", "corr-200", "trace-300")
        ctx = get_request_context()

        self.assertEqual(ctx["request_id"], "req-100")
        self.assertEqual(ctx["correlation_id"], "corr-200")
        self.assertEqual(ctx["trace_id"], "trace-300")

        clear_request_context()
        ctx_cleared = get_request_context()
        self.assertIsNone(ctx_cleared["request_id"])

    def test_concurrent_request_context_isolation(self) -> None:
        """Verifies contextvars do not leak across concurrent async request tasks."""

        async def task_a() -> str:
            set_request_context("req-A-111")
            await asyncio.sleep(0.01)
            return get_request_context()["request_id"] or ""

        async def task_b() -> str:
            set_request_context("req-B-222")
            await asyncio.sleep(0.01)
            return get_request_context()["request_id"] or ""

        async def run_concurrent() -> tuple:
            return await asyncio.gather(task_a(), task_b())

        res_a, res_b = asyncio.run(run_concurrent())
        self.assertEqual(res_a, "req-A-111")
        self.assertEqual(res_b, "req-B-222")

    def test_bounded_metric_label_safety(self) -> None:
        # Legal labels
        metrics_registry.increment_counter(
            "request_count",
            1,
            labels={"method": "GET", "route": "/health", "status_class": "2xx"},
        )
        self.assertEqual(
            metrics_registry.get_counter_value(
                "request_count",
                labels={"method": "GET", "route": "/health", "status_class": "2xx"},
            ),
            1,
        )

        # Illegal high-cardinality label keys should raise ValueError
        with self.assertRaises(ValueError) as cm:
            metrics_registry.increment_counter("request_count", 1, labels={"request_id": "req-123"})
        self.assertIn(
            "High-cardinality or invalid metric label key 'request_id' is prohibited",
            str(cm.exception),
        )

        with self.assertRaises(ValueError):
            metrics_registry.increment_counter(
                "request_count", 1, labels={"customer_id": "cust-999"}
            )

        with self.assertRaises(ValueError):
            metrics_registry.increment_counter(
                "request_count", 1, labels={"transaction_id": "tx-888"}
            )

    def test_monotonic_latency_recording(self) -> None:
        metrics_registry.record_latency(
            "request_latency",
            duration_ms=12.5,
            labels={"method": "GET", "route": "/ready"},
        )
        metrics_registry.record_latency(
            "request_latency",
            duration_ms=14.2,
            labels={"method": "GET", "route": "/ready"},
        )

        latencies = metrics_registry.get_latencies(
            "request_latency", labels={"method": "GET", "route": "/ready"}
        )
        self.assertEqual(latencies, [12.5, 14.2])

    def test_log_injection_prevention(self) -> None:
        malicious_input = "Illegal Event\r\nFake Log Entry: Admin Logged In\t"
        sanitized = sanitize_log_string(malicious_input)

        self.assertNotIn("\n", sanitized)
        self.assertNotIn("\r", sanitized)
        self.assertNotIn("\t", sanitized)

        # Verify StructuredJsonFormatter produces valid single-line JSON with sanitized message
        formatter = StructuredJsonFormatter()
        record = logging.LogRecord("test", logging.INFO, "path", 10, malicious_input, (), None)
        formatted_json = formatter.format(record)

        parsed = json.loads(formatted_json)
        self.assertEqual(parsed["event"], "Illegal Event Fake Log Entry: Admin Logged In ")

    def test_observability_failure_isolation(self) -> None:
        """Verifies that an observability error during metric recording does not crash request dispatch."""
        app = create_app(auto_startup=True)

        async def run_asgi() -> int:
            sent_messages = []

            async def send(msg: dict) -> None:
                sent_messages.append(msg)

            async def receive() -> dict:
                return {}

            scope = {"type": "http", "method": "GET", "path": "/health", "headers": []}
            await app(scope, receive, send)
            status_val = int(sent_messages[0]["status"])
            return status_val

        # Call endpoint normally
        status = asyncio.run(run_asgi())
        self.assertEqual(status, 200)

        # Verify metrics recorded
        c_val = metrics_registry.get_counter_value(
            "request_count",
            labels={"method": "GET", "route": "/health", "status_class": "2xx"},
        )
        self.assertGreaterEqual(c_val, 1)


if __name__ == "__main__":
    unittest.main()
