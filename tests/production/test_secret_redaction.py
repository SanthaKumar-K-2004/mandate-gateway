"""
Unit tests for Production Secret Redaction (M29 - Workstream 5).
"""

from __future__ import annotations

import unittest

from apps.api.observability.structured_logger import SecretRedactor


class TestSecretRedaction(unittest.TestCase):
    """SecretRedactor test suite."""

    def test_01_dict_key_redaction(self) -> None:
        """Verify API keys, passwords, and tokens are redacted from dicts."""
        data = {
            "api_key": "live_sec_123456789",
            "user_password": "SuperSecretPassword123!",
            "normal_field": "public_data",
            "nested": {"hmac_secret": "abc_secret_key_xyz"},
        }
        clean = SecretRedactor.sanitize_dict(data)

        self.assertEqual(clean["api_key"], "[REDACTED]")
        self.assertEqual(clean["user_password"], "[REDACTED]")
        self.assertEqual(clean["normal_field"], "public_data")
        self.assertEqual(clean["nested"]["hmac_secret"], "[REDACTED]")

    def test_02_bearer_token_string_redaction(self) -> None:
        """Verify Bearer tokens in free-text messages are sanitized."""
        msg = "Sending request with Auth Header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        clean = SecretRedactor.sanitize_string(msg)

        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", clean)
        self.assertIn("[REDACTED]", clean)
