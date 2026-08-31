"""
Unit tests for Signed Merchant Webhook Processing (M25).
"""

from __future__ import annotations

import hashlib
import hmac
import time
import unittest

from apps.api.commerce.models import OrderStatus
from apps.api.commerce.webhooks import CommerceWebhookHandler, WebhookValidationError


class TestCommerceWebhooks(unittest.TestCase):
    """CommerceWebhookHandler test suite."""

    def test_01_verify_valid_signed_webhook(self) -> None:
        """Verify valid HMAC-SHA256 signed webhook processing."""
        secret = "whsec_cafe_acme_live_m25"
        handler = CommerceWebhookHandler(webhook_secret=secret)

        now_ts = int(time.time())
        event_id = "evt_acme_9001"
        payload = {
            "event": "order.confirmed",
            "merchant_order_id": "m_ord_acme_55",
            "payment_transaction_id": "txn_pay_55",
            "amount_paise": 14000,
            "currency": "INR",
        }
        raw_body = str(payload).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        res = handler.process_webhook(
            raw_body=raw_body,
            signature=f"sha256={signature}",
            event_id=event_id,
            timestamp_header=str(now_ts),
            payload=payload,
        )

        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["order_status"], OrderStatus.ORDER_VERIFIED.value)

    def test_02_invalid_signature_rejected(self) -> None:
        """Verify webhook with invalid HMAC signature is rejected."""
        handler = CommerceWebhookHandler(webhook_secret="whsec_cafe_acme_live_m25")
        raw_body = b'{"event": "order.confirmed"}'

        with self.assertRaises(WebhookValidationError):
            handler.process_webhook(
                raw_body=raw_body,
                signature="sha256=invalid_signature_hash",
                event_id="evt_invalid_01",
                timestamp_header=str(int(time.time())),
                payload={},
            )

    def test_03_expired_timestamp_rejected(self) -> None:
        """Verify webhook with timestamp older than 300 seconds is rejected."""
        secret = "whsec_cafe_acme_live_m25"
        handler = CommerceWebhookHandler(webhook_secret=secret)

        expired_ts = int(time.time()) - 400  # 400s old > 300s limit!
        raw_body = b'{"event": "order.confirmed"}'
        signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        with self.assertRaises(WebhookValidationError):
            handler.process_webhook(
                raw_body=raw_body,
                signature=signature,
                event_id="evt_expired_01",
                timestamp_header=str(expired_ts),
                payload={},
            )

    def test_04_idempotency_prevents_duplicate_processing(self) -> None:
        """Verify duplicate event ID is handled idempotently without re-execution."""
        secret = "whsec_cafe_acme_live_m25"
        handler = CommerceWebhookHandler(webhook_secret=secret)

        now_ts = int(time.time())
        event_id = "evt_acme_idempotent_1"
        payload = {"event": "order.confirmed", "merchant_order_id": "m_ord_1"}
        raw_body = str(payload).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        res1 = handler.process_webhook(raw_body, signature, event_id, str(now_ts), payload)
        self.assertEqual(res1["status"], "SUCCESS")

        # Second call with same event_id
        res2 = handler.process_webhook(raw_body, signature, event_id, str(now_ts), payload)
        self.assertEqual(res2["status"], "DUPLICATE")
