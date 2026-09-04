"""
M19 Webhook Security Adversarial Test Suite
==========================================
Workstream 10 — Evaluates HMAC-SHA256 signature verification, signature forgery detection,
and invalid HMAC payload tampering rejection.
"""

from __future__ import annotations

import hashlib
import hmac
import unittest

from sdk.python.razorpay import RazorpayWebhookVerifier


class TestM19WebhookSecurity(unittest.TestCase):
    """Adversarial security test suite for webhook signatures."""

    def test_01_signature_verification_success(self) -> None:
        """Verify valid HMAC-SHA256 signature passes verification."""
        secret = "whsec_live_key_998877"
        raw_payload = b'{"event":"payment.captured","amount_paise":5000}'
        sig = hmac.new(secret.encode("utf-8"), raw_payload, hashlib.sha256).hexdigest()

        is_valid = RazorpayWebhookVerifier.verify_signature(raw_payload, sig, secret)
        self.assertTrue(is_valid)

    def test_02_forged_signature_rejection(self) -> None:
        """Verify forged signature is rejected immediately."""
        secret = "whsec_live_key_998877"
        raw_payload = b'{"event":"payment.captured","amount_paise":5000}'

        is_valid = RazorpayWebhookVerifier.verify_signature(
            raw_payload, "deadbeefcafebabe1234567890abcdef", secret
        )
        self.assertFalse(is_valid)

    def test_03_tampered_payload_rejection(self) -> None:
        """Verify modified payload bytes fail verification against original signature."""
        secret = "whsec_live_key_998877"
        raw_payload_original = b'{"event":"payment.captured","amount_paise":5000}'
        raw_payload_tampered = b'{"event":"payment.captured","amount_paise":50000}'

        sig = hmac.new(secret.encode("utf-8"), raw_payload_original, hashlib.sha256).hexdigest()

        is_valid = RazorpayWebhookVerifier.verify_signature(raw_payload_tampered, sig, secret)
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()
