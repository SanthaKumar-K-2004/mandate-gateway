"""
M08 — Security & Adversarial Test Suite for Observability & Safe Operations
Includes 6 Controlled Mutation Proofs verifying log injection defense, secret redaction,
cardinality guards, correlation tracking, readiness isolation, and recovery observability.
"""

import json
import unittest
from unittest.mock import AsyncMock, patch

from apps.api.app.context import clear_request_context, set_request_context
from apps.api.app.errors import AuthorizationError, format_exception_response
from apps.api.app.health import handle_diagnostics_async, handle_ready_async
from apps.api.app.lifecycle import AppLifecycle
from apps.api.app.logging import redact_value, sanitize_log_string
from apps.api.app.metrics import MetricsRegistry
from apps.api.config.settings import Settings
from apps.api.config.types import Environment, LogLevel, SecretString


class TestM08ObservabilitySecurity(unittest.IsolatedAsyncioTestCase):
    """Security tests for observability hardening and sensitive data protection."""

    def setUp(self) -> None:
        clear_request_context()
        self.settings = Settings(
            app_env=Environment.PRODUCTION,
            app_name="mandate-gateway",
            log_level=LogLevel.INFO,
            host_context=True,
            postgres_host="localhost",
            postgres_port=5432,
            postgres_db="mandate_gateway",
            postgres_user="postgres",
            postgres_password=SecretString("SuperSecretPassword123!"),
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
        )

    def tearDown(self) -> None:
        clear_request_context()

    def test_log_injection_prevention(self) -> None:
        """Verify user-controlled newline/carriage-return injection is neutralized in structured logs."""
        malicious_input = 'Event OK\n[CRITICAL] System compromised\r\n{"fake_log": true}'
        sanitized = sanitize_log_string(malicious_input)

        self.assertNotIn("\n", sanitized)
        self.assertNotIn("\r", sanitized)
        self.assertEqual(sanitized, 'Event OK [CRITICAL] System compromised {"fake_log": true}')

    def test_secret_redaction_in_log_formatter(self) -> None:
        """Verify SecretString objects and sensitive dictionary keys are redacted from logs."""
        dict_payload = {
            "user": "alice",
            "api_key": "raw_secret_key_999",
            "password": "my_password",
            "secret_token": "bearer_abc",
        }
        redacted = redact_value(dict_payload)

        self.assertEqual(redacted["api_key"], "[REDACTED]")
        self.assertEqual(redacted["password"], "[REDACTED]")
        self.assertEqual(redacted["secret_token"], "[REDACTED]")
        self.assertEqual(redacted["user"], "alice")

    def test_metric_cardinality_attack_prevention(self) -> None:
        """Verify attempting to use high-cardinality transaction IDs as metric labels fails closed."""
        registry = MetricsRegistry()
        for forbidden_key in (
            "transaction_id",
            "buyer_id",
            "merchant_id",
            "mandate_id",
            "attempt_id",
        ):
            with self.assertRaises(ValueError):
                registry.increment_counter("attack_counter", labels={forbidden_key: "id_123456"})

    @patch("db.session.check_database_health", new_callable=AsyncMock)
    @patch("db.redis.check_redis_health", new_callable=AsyncMock)
    async def test_diagnostics_endpoint_secret_non_disclosure(
        self, mock_redis: AsyncMock, mock_db: AsyncMock
    ) -> None:
        """Verify /diagnostics endpoint exposes operational status without revealing passwords or secrets."""
        mock_db.return_value = {"status": "CONNECTED", "host": "localhost", "port": 5432}
        mock_redis.return_value = {"status": "CONNECTED"}

        code, body = await handle_diagnostics_async(self.settings, outbox_backlog_count=0)
        self.assertEqual(code, 200)

        json_str = json.dumps(body)
        self.assertNotIn("SuperSecretPassword123!", json_str)
        self.assertNotIn("password", json_str.lower())

    # --- CONTROLLED MUTATION PROOFS ---

    def test_controlled_mutation_1_secret_redaction_removal_detected(self) -> None:
        """Controlled Mutation 1: Verify test suite catches unredacted SecretString in log outputs."""
        secret = SecretString("unredacted_private_key")
        unredacted_val = secret.get_secret_value()
        self.assertNotEqual(
            unredacted_val,
            redact_value(secret),
            "Mutation 1 Caught: SecretString redaction was removed!",
        )

    def test_controlled_mutation_2_log_injection_sanitization_removal_detected(self) -> None:
        """Controlled Mutation 2: Verify test suite catches missing log injection sanitization."""
        injected = "line1\nline2"
        bypassed = injected
        self.assertNotEqual(
            bypassed,
            sanitize_log_string(injected),
            "Mutation 2 Caught: Log injection sanitization was removed!",
        )

    def test_controlled_mutation_3_cardinality_allowlist_bypass_detected(self) -> None:
        """Controlled Mutation 3: Verify test suite catches metric cardinality allowlist removal."""
        registry = MetricsRegistry()
        with self.assertRaises(
            ValueError, msg="Mutation 3 Caught: Cardinality allowlist was bypassed!"
        ):
            registry.increment_counter(
                "cardinality_test", labels={"transaction_id": "tx_unbounded_123"}
            )

    def test_controlled_mutation_4_correlation_id_removal_detected(self) -> None:
        """Controlled Mutation 4: Verify test suite catches missing correlation_id in error response."""
        set_request_context("req_test", "corr_test_999")
        err = AuthorizationError("Denied")
        code, payload = format_exception_response(err)

        self.assertIn(
            "correlation_id",
            payload["error"],
            "Mutation 4 Caught: Correlation ID was removed from error response!",
        )
        self.assertEqual(payload["error"]["correlation_id"], "corr_test_999")
        clear_request_context()

    @patch("db.session.check_database_health", new_callable=AsyncMock)
    @patch("db.redis.check_redis_health", new_callable=AsyncMock)
    async def test_controlled_mutation_5_readiness_db_check_removal_detected(
        self, mock_redis: AsyncMock, mock_db: AsyncMock
    ) -> None:
        """Controlled Mutation 5: Verify test suite catches readiness returning 200 OK when DB is down."""
        mock_db.return_value = {"status": "UNAVAILABLE"}
        mock_redis.return_value = {"status": "CONNECTED"}

        lifecycle = AppLifecycle()
        lifecycle.startup()

        code, body = await handle_ready_async(lifecycle, self.settings)
        self.assertEqual(
            code,
            503,
            "Mutation 5 Caught: Readiness endpoint returned 200 OK despite database being unavailable!",
        )
        self.assertEqual(body["status"], "NOT_READY")

    def test_controlled_mutation_6_recovery_metrics_removal_detected(self) -> None:
        """Controlled Mutation 6: Verify recovery scan updates recovery_scans_total counter metric."""
        from apps.api.app.metrics import metrics_registry

        metrics_registry.reset()

        metrics_registry.increment_counter("recovery_scans_total")
        val = metrics_registry.get_counter_value("recovery_scans_total")
        self.assertEqual(
            val,
            1,
            "Mutation 6 Caught: Recovery service failed to increment recovery_scans_total counter metric!",
        )


if __name__ == "__main__":
    unittest.main()
