"""
M19 Python Developer SDK Acceptance Suite
=========================================
Workstream 9 — Tests Python Developer SDK client construction, mandate creation,
payment submission, webhook signature verification, and error handling.
"""

from __future__ import annotations

import unittest
from sdk.python.razerpay import (
    RazerpayClient,
    RazerpayConfig,
    ValidationError,
)


class TestM19PythonSDK(unittest.TestCase):
    """Python Developer SDK acceptance suite."""

    def setUp(self) -> None:
        self.config = RazerpayConfig(
            base_url="http://localhost:8000",
            api_key="rzp_test_sdk_key_99",
            merchant_id="mer_sdk_test",
        )
        self.client = RazerpayClient(self.config)

    def test_01_mandate_creation(self) -> None:
        """Verify SDK mandate creation produces valid MandateResponse object."""
        mandate = self.client.create_mandate(
            buyer_id="buy_sdk_user_1",
            daily_budget_paise=100000,
        )
        self.assertTrue(mandate.mandate_id.startswith("man_"))
        self.assertEqual(mandate.merchant_id, "mer_sdk_test")
        self.assertEqual(mandate.buyer_id, "buy_sdk_user_1")
        self.assertEqual(mandate.daily_budget_paise, 100000)
        self.assertEqual(mandate.status, "ACTIVE")

    def test_02_payment_submission(self) -> None:
        """Verify SDK payment submission generates transaction and idempotency keys."""
        tx = self.client.submit_payment(
            mandate_id="man_sdk_100",
            amount_paise=5000,
            idempotency_key="idemp_sdk_test_01",
        )
        self.assertEqual(tx.merchant_id, "mer_sdk_test")
        self.assertEqual(tx.mandate_id, "man_sdk_100")
        self.assertEqual(tx.amount_paise, 5000)
        self.assertEqual(tx.state, "COMMITTED")
        self.assertEqual(tx.auth_decision, "ALLOW")
        self.assertIsNotNone(tx.action_receipt_signature)

    def test_03_payment_validation_error(self) -> None:
        """Verify invalid payment amount raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.client.submit_payment(
                mandate_id="man_sdk_100",
                amount_paise=-100,
            )

    def test_04_webhook_subscription(self) -> None:
        """Verify SDK registers webhook subscriptions."""
        sub = self.client.register_webhook(
            url="https://merchant.example.com/webhooks",
            events=["payment.captured", "payment.failed"],
        )
        self.assertTrue(sub.subscription_id.startswith("sub_"))
        self.assertEqual(sub.merchant_id, "mer_sdk_test")
        self.assertEqual(sub.url, "https://merchant.example.com/webhooks")
        self.assertIn("payment.captured", sub.events)

    def test_05_webhook_signature_verification(self) -> None:
        """Verify SDK HMAC-SHA256 signature verification helper."""
        secret = "whsec_test_secret_key_88"
        raw_payload = b'{"event":"payment.captured","transaction_id":"tx_100"}'

        import hashlib
        import hmac

        expected_sig = hmac.new(
            secret.encode("utf-8"),
            raw_payload,
            hashlib.sha256,
        ).hexdigest()

        # Valid signature
        is_valid = self.client.verify_webhook_signature(
            raw_payload=raw_payload,
            signature=expected_sig,
            secret=secret,
        )
        self.assertTrue(is_valid)

        # Forged signature
        is_forged = self.client.verify_webhook_signature(
            raw_payload=raw_payload,
            signature="forged_signature_hex_digest",
            secret=secret,
        )
        self.assertFalse(is_forged)


if __name__ == "__main__":
    unittest.main()
