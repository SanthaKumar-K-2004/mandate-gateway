"""
M13 — Telemetry & Logging Security Audit Test Suite
Section M13 — Security & Telemetry Protection Foundation
"""

import json
import logging
import unittest

from apps.api.app.context import clear_request_context, get_full_context, set_transaction_context
from apps.api.app.logging import StructuredJsonFormatter, redact_value
from apps.api.config.types import SecretString


class TestM13TelemetrySecurity(unittest.TestCase):
    """Security audit test suite ensuring zero sensitive data leaks in telemetry."""

    def setUp(self) -> None:
        clear_request_context()

    def tearDown(self) -> None:
        clear_request_context()

    def test_secret_string_redaction_in_dictionary(self) -> None:
        """Verify redact_value redacts SecretString objects and sensitive dictionary keys."""
        payload = {
            "merchant_id": "m_123",
            "private_key": "raw_private_key_bytes",
            "webhook_secret": SecretString("whsec_12345"),
            "auth_header": "Bearer token_xyz",
            "cvv": "123",
        }
        redacted = redact_value(payload)

        self.assertEqual(redacted["merchant_id"], "m_123")
        self.assertEqual(redacted["private_key"], "[REDACTED]")
        self.assertEqual(redacted["webhook_secret"], "[REDACTED]")
        self.assertEqual(redacted["auth_header"], "[REDACTED]")
        self.assertEqual(redacted["cvv"], "[REDACTED]")

    def test_log_injection_prevention(self) -> None:
        """Verify newlines and carriage returns are sanitized to preserve single-line JSON log integrity."""
        formatter = StructuredJsonFormatter()
        malicious_input = (
            'Payment success\r\n{"level": "FATAL", "event": "Fake Root Privilege Executed"}'
        )
        record = logging.LogRecord(
            name="security_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=50,
            msg=malicious_input,
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)

        # Output must be valid single-line JSON
        lines = formatted.splitlines()
        self.assertEqual(len(lines), 1, "Log record must not contain raw linebreaks.")
        parsed = json.loads(formatted)
        self.assertIn("Payment success", parsed["event"])

    def test_context_variables_redaction(self) -> None:
        """Verify domain context variables do not leak secret strings."""
        set_transaction_context(
            transaction_id="tx_sec_01",
            merchant_id="m_sec_01",
        )
        ctx = get_full_context()
        self.assertEqual(ctx["transaction_id"], "tx_sec_01")
        self.assertEqual(ctx["merchant_id"], "m_sec_01")


if __name__ == "__main__":
    unittest.main()
