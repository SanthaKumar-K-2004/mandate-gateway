"""
M13 — Security Test Suite for Observability & Control Plane (S01 - S06)
Section 10 & 14 — Security Requirements
"""

import logging
import unittest
from unittest.mock import AsyncMock, patch

from apps.api.app.context import clear_request_context
from apps.api.app.health import handle_ready_async
from apps.api.app.lifecycle import AppLifecycle
from apps.api.app.logging import SecretRedactionFilter, StructuredJsonFormatter
from apps.api.app.metrics import metrics_registry
from apps.api.app.middleware import sanitize_or_generate_id
from apps.api.config.helpers import get_settings
from apps.api.config.types import Environment
from apps.api.observability.alerting import alert_evaluator
from apps.api.observability.investigation import TransactionInvestigator


class TestM13ObservabilitySecurity(unittest.IsolatedAsyncioTestCase):
    """Security test suite verifying S01 through S06 observability security controls."""

    def setUp(self) -> None:
        clear_request_context()
        metrics_registry.reset()
        alert_evaluator.clear_alerts()

    def test_S01_correlation_id_injection_sanitization(self) -> None:
        """S01: Verify malicious correlation IDs with newlines and control chars are safely sanitized/rejected."""
        malicious_inputs = [
            "corr_123\r\nHTTP/1.1 200 OK\r\nHeader: injected",
            "corr_123\nLOG_INJECTION_LINE",
            "corr_123\x00NULL_BYTE",
            "../../etc/passwd",
            "<script>alert(1)</script>",
        ]
        for mal in malicious_inputs:
            sanitized = sanitize_or_generate_id(mal)
            self.assertNotIn("\n", sanitized)
            self.assertNotIn("\r", sanitized)
            self.assertNotIn("\x00", sanitized)
            self.assertNotIn("<script>", sanitized)
            # Must fall back to safe generated UUID
            self.assertEqual(len(sanitized), 36)

    def test_S02_cross_merchant_investigation_fails_closed(self) -> None:
        """S02: Verify querying another merchant's transaction fails closed with PermissionError."""
        inv = TransactionInvestigator()
        tx_id = "tx_s02_secure"
        inv.register_transaction(
            tx_id,
            {
                "transaction_id": tx_id,
                "merchant_id": "merchant_alpha",
                "buyer_id": "buyer_01",
                "state": "COMMITTED",
            },
        )

        with self.assertRaises(PermissionError):
            inv.investigate(tx_id, requesting_merchant_id="merchant_beta_attacker")

    def test_S03_sensitive_telemetry_leakage_prevented(self) -> None:
        """S03: Verify logs and investigation responses do not expose secrets or private keys."""
        formatter = StructuredJsonFormatter(
            service_name="mandate-gateway", environment="production"
        )
        redaction_filter = SecretRedactionFilter()

        record = logging.LogRecord(
            name="security_logger",
            level=logging.ERROR,
            pathname="security.py",
            lineno=42,
            msg="Payment authorization error for private_key=0xabcdef1234567890 and secret=sec_9999",
            args=(),
            exc_info=None,
        )

        self.assertTrue(redaction_filter.filter(record))
        log_json = formatter.format(record)

        self.assertNotIn("0xabcdef1234567890", log_json)
        self.assertNotIn("sec_9999", log_json)
        self.assertIn("[REDACTED]", log_json)

    def test_S04_high_cardinality_metric_attack_blocked(self) -> None:
        """S04: Verify attacker-controlled identifiers as metric labels are rejected with ValueError."""
        attacker_labels = {
            "transaction_id": "tx_attacker_injected_123456789",
            "buyer_id": "buyer_malicious",
            "idempotency_key": "idemp_attack_999",
        }
        for k, v in attacker_labels.items():
            with self.assertRaises(ValueError):
                metrics_registry.increment_counter("payments_created_total", labels={k: v})

    def test_S05_audit_integrity_alert_activation(self) -> None:
        """S05: Verify audit hash-chain verification failure increments metric and triggers CRITICAL alert."""
        # Record audit integrity failure metric
        metrics_registry.increment_counter(
            "audit_integrity_failures_total", labels={"service": "mandate-gateway"}
        )
        self.assertEqual(
            metrics_registry.get_counter_value(
                "audit_integrity_failures_total", labels={"service": "mandate-gateway"}
            ),
            1,
        )

        # Trigger alert evaluator for audit chain tamper
        alert = alert_evaluator.evaluate_rule(
            rule_name="audit_chain_verification_failure",
            metric_value=1.0,
            threshold=1.0,
        )
        self.assertIsNotNone(alert)
        assert alert is not None
        self.assertEqual(alert["severity"], "CRITICAL")

    @patch("db.session.check_database_health", new_callable=AsyncMock)
    @patch("db.redis.check_redis_health", new_callable=AsyncMock)
    async def test_S06_dependency_health_deception_prevented(
        self, mock_redis: AsyncMock, mock_db: AsyncMock
    ) -> None:
        """S06: Verify readiness probe in production returns 503 and fails closed when DB fails."""
        import dataclasses

        prod_settings = dataclasses.replace(get_settings(), app_env=Environment.PRODUCTION)
        lifecycle = AppLifecycle()
        lifecycle.startup()

        mock_db.return_value = {"status": "DISCONNECTED", "error": "PostgreSQL down"}
        mock_redis.return_value = {"status": "CONNECTED"}

        status_code, body = await handle_ready_async(lifecycle, prod_settings)
        self.assertEqual(status_code, 503)
        self.assertEqual(body["status"], "NOT_READY")


if __name__ == "__main__":
    unittest.main()
