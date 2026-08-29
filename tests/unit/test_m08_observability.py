"""
M08 — Unit Test Suite for Observability, Metrics, Health, and Exception Translation
"""

import json
import logging
import unittest
from unittest.mock import AsyncMock, patch

from apps.api.app.context import (
    clear_request_context,
    get_full_context,
    set_request_context,
    set_transaction_context,
)
from apps.api.app.errors import (
    AuthorizationError,
    format_exception_response,
)
from apps.api.app.health import (
    handle_diagnostics_async,
    handle_health,
    handle_ready,
    handle_ready_async,
)
from apps.api.app.lifecycle import AppLifecycle
from apps.api.app.logging import (
    StructuredJsonFormatter,
    redact_value,
    sanitize_log_string,
)
from apps.api.app.metrics import MetricsRegistry
from apps.api.config.settings import Settings, validate_production_config
from apps.api.config.types import ConfigurationError, Environment, LogLevel, SecretString


class TestM08ContextAndLogging(unittest.TestCase):
    """Test contextvars propagation and structured JSON logging formatting."""

    def setUp(self) -> None:
        clear_request_context()

    def tearDown(self) -> None:
        clear_request_context()

    def test_contextvars_set_and_clear(self) -> None:
        set_request_context("req_123", "corr_456", "trace_789")
        set_transaction_context(
            transaction_id="tx_abc",
            merchant_id="mer_1",
            buyer_id="buy_2",
            mandate_id="man_3",
            execution_attempt_id="att_4",
            outbox_event_id="evt_5",
        )

        ctx = get_full_context()
        self.assertEqual(ctx["request_id"], "req_123")
        self.assertEqual(ctx["correlation_id"], "corr_456")
        self.assertEqual(ctx["trace_id"], "trace_789")
        self.assertEqual(ctx["transaction_id"], "tx_abc")
        self.assertEqual(ctx["merchant_id"], "mer_1")

        clear_request_context()
        cleared_ctx = get_full_context()
        self.assertIsNone(cleared_ctx["request_id"])
        self.assertIsNone(cleared_ctx["transaction_id"])

    def test_log_string_sanitization(self) -> None:
        dirty = "line1\r\nline2\nline3\tline4"
        clean = sanitize_log_string(dirty)
        self.assertEqual(clean, "line1 line2 line3 line4")

    def test_redact_value(self) -> None:
        secret = SecretString("super_secret_key")
        self.assertEqual(redact_value(secret), "[REDACTED]")
        self.assertEqual(
            redact_value({"api_key": "raw_key", "public": "ok"}),
            {"api_key": "[REDACTED]", "public": "ok"},
        )
        self.assertEqual(redact_value({"password": "pass"}), {"password": "[REDACTED]"})

    def test_structured_json_formatter(self) -> None:
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
        set_request_context("req_111", "corr_222", "trace_333")
        set_transaction_context(transaction_id="tx_999", merchant_id="mer_888")

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        self.assertEqual(parsed["service"], "test-service")
        self.assertEqual(parsed["event"], "Payment processed successfully")
        self.assertEqual(parsed["request_id"], "req_111")
        self.assertEqual(parsed["correlation_id"], "corr_222")
        self.assertEqual(parsed["transaction_id"], "tx_999")
        self.assertEqual(parsed["merchant_id"], "mer_888")


class TestM08MetricsRegistry(unittest.TestCase):
    """Test metrics registry counter, gauge, latency, and label cardinality protection."""

    def setUp(self) -> None:
        self.registry = MetricsRegistry()

    def test_counter_and_gauge(self) -> None:
        self.registry.increment_counter("payments_total", value=1, labels={"status": "COMMITTED"})
        self.assertEqual(
            self.registry.get_counter_value("payments_total", labels={"status": "COMMITTED"}), 1
        )

        self.registry.set_gauge("outbox_pending_events", value=42.0)
        self.assertEqual(self.registry.get_gauge_value("outbox_pending_events"), 42.0)

    def test_latency_recording(self) -> None:
        self.registry.record_latency(
            "provider_latency_ms", duration_ms=125.5, labels={"operation": "DEBIT"}
        )
        latencies = self.registry.get_latencies(
            "provider_latency_ms", labels={"operation": "DEBIT"}
        )
        self.assertEqual(latencies, [125.5])

    def test_high_cardinality_label_rejection(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.registry.increment_counter("bad_metric", labels={"transaction_id": "tx_12345"})
        self.assertIn(
            "High-cardinality or invalid metric label key 'transaction_id' is prohibited",
            str(ctx.exception),
        )


class TestM08HealthAndReadiness(unittest.IsolatedAsyncioTestCase):
    """Test /health, /ready, and /diagnostics endpoint handlers."""

    def setUp(self) -> None:
        self.settings = Settings(
            app_env=Environment.PRODUCTION,
            app_name="mandate-gateway",
            log_level=LogLevel.INFO,
            host_context=True,
            postgres_host="localhost",
            postgres_port=5432,
            postgres_db="mandate_gateway",
            postgres_user="postgres",
            postgres_password=SecretString("postgres"),
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
        )
        self.lifecycle = AppLifecycle()

    def test_handle_health(self) -> None:
        code, body = handle_health(self.settings)
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "HEALTHY")

    def test_handle_ready_sync(self) -> None:
        code, body = handle_ready(self.lifecycle, self.settings)
        self.assertEqual(code, 503)
        self.assertEqual(body["status"], "NOT_READY")

        self.lifecycle.startup()
        code2, body2 = handle_ready(self.lifecycle, self.settings)
        self.assertEqual(code2, 200)
        self.assertEqual(body2["status"], "READY")

    @patch("db.session.check_database_health", new_callable=AsyncMock)
    @patch("db.redis.check_redis_health", new_callable=AsyncMock)
    async def test_handle_ready_async_success(
        self, mock_redis: AsyncMock, mock_db: AsyncMock
    ) -> None:
        mock_db.return_value = {"status": "CONNECTED"}
        mock_redis.return_value = {"status": "CONNECTED"}
        self.lifecycle.startup()

        code, body = await handle_ready_async(self.lifecycle, self.settings)
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "READY")

    @patch("db.session.check_database_health", new_callable=AsyncMock)
    @patch("db.redis.check_redis_health", new_callable=AsyncMock)
    async def test_handle_ready_async_dependency_down(
        self, mock_redis: AsyncMock, mock_db: AsyncMock
    ) -> None:
        mock_db.return_value = {"status": "UNAVAILABLE"}
        mock_redis.return_value = {"status": "CONNECTED"}
        self.lifecycle.startup()

        code, body = await handle_ready_async(self.lifecycle, self.settings)
        self.assertEqual(code, 503)
        self.assertEqual(body["status"], "NOT_READY")

    @patch("db.session.check_database_health", new_callable=AsyncMock)
    @patch("db.redis.check_redis_health", new_callable=AsyncMock)
    async def test_handle_diagnostics(self, mock_redis: AsyncMock, mock_db: AsyncMock) -> None:
        mock_db.return_value = {"status": "CONNECTED"}
        mock_redis.return_value = {"status": "CONNECTED"}

        code, body = await handle_diagnostics_async(
            self.settings, outbox_backlog_count=5, recovery_stuck_count=0
        )
        self.assertEqual(code, 200)
        self.assertEqual(body["subsystems"]["outbox"]["backlog_pending_count"], 5)


class TestM08ConfigValidationAndErrors(unittest.TestCase):
    """Test production configuration fail-fast validation and exception formatting."""

    def test_production_config_validation(self) -> None:
        insecure_settings = Settings(
            app_env=Environment.PRODUCTION,
            app_name="mandate-gateway",
            log_level=LogLevel.INFO,
            host_context=False,
            postgres_host="postgres",
            postgres_port=5432,
            postgres_db="mandate_gateway",
            postgres_user="postgres",
            postgres_password=SecretString("postgres"),  # Default password prohibited in prod
            redis_host="redis",
            redis_port=6379,
            redis_db=0,
        )
        with self.assertRaises(ConfigurationError) as ctx:
            validate_production_config(insecure_settings)
        self.assertIn("Insecure or default POSTGRES_PASSWORD prohibited", str(ctx.exception))

    def test_format_exception_response(self) -> None:
        set_request_context("req_abc", "corr_xyz")

        auth_err = AuthorizationError("Access denied to merchant data")
        code, body = format_exception_response(auth_err)
        self.assertEqual(code, 403)
        self.assertEqual(body["error"]["code"], "AUTHORIZATION_DENIED")
        self.assertEqual(body["error"]["correlation_id"], "corr_xyz")

        unhandled = ValueError("Unexpected internal exception")
        code2, body2 = format_exception_response(unhandled)
        self.assertEqual(code2, 500)
        self.assertEqual(body2["error"]["code"], "INTERNAL_SERVER_ERROR")

        clear_request_context()


if __name__ == "__main__":
    unittest.main()
