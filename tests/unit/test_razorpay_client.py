"""
Unit tests for Razorpay Client REST API connector and signature verification.
"""

import unittest
from apps.api.commerce.payments import (
    PaymentState,
    RazorpayClient,
    RazorpayClientError,
    RazorpayMode,
)
from apps.api.config.types import SecretString


class TestRazorpayClient(unittest.TestCase):

    def setUp(self) -> None:
        self.client = RazorpayClient(
            key_id=SecretString("rzp_test_key_12345678"),
            key_secret=SecretString("rzp_test_secret_87654321"),
            webhook_secret=SecretString("whsec_test_secret_123456"),
            mode=RazorpayMode.TEST,
        )
        self.mock_client = RazorpayClient()  # Unconfigured fallback mock mode

    def test_mode_and_configuration(self) -> None:
        self.assertEqual(self.client.mode, RazorpayMode.TEST)
        self.assertTrue(self.client.is_configured)
        self.assertFalse(self.mock_client.is_configured)

    def test_create_test_order_mock(self) -> None:
        order = self.mock_client.create_test_order(
            amount_paise=29900,
            currency="INR",
            receipt="rcpt_unit_001",
            notes={"item": "coffee"},
        )
        self.assertTrue(order.order_id.startswith("order_test_rcpt_unit_"))
        self.assertEqual(order.amount_paise, 29900)
        self.assertEqual(order.currency, "INR")
        self.assertEqual(order.mode, RazorpayMode.TEST)

    def test_invalid_order_amount(self) -> None:
        with self.assertRaises(RazorpayClientError):
            self.client.create_test_order(amount_paise=-500)
        with self.assertRaises(RazorpayClientError):
            self.client.create_test_order(amount_paise=0)

    def test_fetch_order(self) -> None:
        created = self.mock_client.create_test_order(amount_paise=15000, receipt="rcpt_002")
        fetched = self.mock_client.fetch_order(created.order_id)
        self.assertEqual(fetched.order_id, created.order_id)
        self.assertEqual(fetched.amount_paise, 15000)

    def test_fetch_payment_status(self) -> None:
        details = self.mock_client.fetch_payment("pay_test_123")
        self.assertEqual(details.status, "captured")
        status_enum = self.mock_client.get_payment_status("pay_test_123")
        self.assertEqual(status_enum, PaymentState.CAPTURED)

    def test_verify_payment_signature(self) -> None:
        order_id = "order_N12345"
        payment_id = "pay_N67890"
        secret = "rzp_test_secret_87654321"

        import hmac
        import hashlib

        msg = f"{order_id}|{payment_id}".encode("utf-8")
        valid_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

        self.assertTrue(self.client.verify_payment_signature(order_id, payment_id, valid_sig))
        self.assertFalse(self.client.verify_payment_signature(order_id, payment_id, "invalid_sig"))

    def test_verify_webhook_signature(self) -> None:
        body = b'{"event":"payment.captured"}'
        secret = "whsec_test_secret_123456"

        import hmac
        import hashlib

        valid_sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        self.assertTrue(self.client.verify_webhook_signature(body, valid_sig))
        self.assertFalse(self.client.verify_webhook_signature(body, "invalid_wh_sig"))


if __name__ == "__main__":
    unittest.main()
