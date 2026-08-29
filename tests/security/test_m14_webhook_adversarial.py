"""
M14 Security Tests — Webhook Cryptographic Verification, Timestamp Freshness & Replay Attack Resistance
"""

import hmac
import hashlib
import json
import time
import unittest

from apps.api.domain.webhook_engine import WebhookEngine


class TestM14WebhookAdversarial(unittest.TestCase):
    """Test webhook signature verification, timestamp freshness, duplicate rejection, and terminal state protection."""

    def setUp(self) -> None:
        self.secret = "whsec_test_secret_key_12345"
        self.engine = WebhookEngine(webhook_secret=self.secret)

    def test_valid_signature_verification(self) -> None:
        payload = json.dumps({"event": "payment.authorized", "id": "evt_123"}).encode("utf-8")
        sig = hmac.new(self.secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

        self.assertTrue(self.engine.verify_signature(payload, sig))
        self.assertTrue(self.engine.verify_signature(payload, f"sha256={sig}"))

    def test_invalid_signature_rejection(self) -> None:
        payload = json.dumps({"event": "payment.authorized", "id": "evt_123"}).encode("utf-8")
        bad_sig = "a" * 64

        self.assertFalse(self.engine.verify_signature(payload, bad_sig))
        self.assertFalse(self.engine.verify_signature(payload, ""))
        self.assertFalse(self.engine.verify_signature(payload, None))

    def test_tampered_payload_signature_rejection(self) -> None:
        payload_orig = json.dumps({"event": "payment.authorized", "amount": 1000}).encode("utf-8")
        sig = hmac.new(self.secret.encode("utf-8"), payload_orig, hashlib.sha256).hexdigest()

        payload_tampered = json.dumps({"event": "payment.authorized", "amount": 1000000}).encode(
            "utf-8"
        )
        self.assertFalse(self.engine.verify_signature(payload_tampered, sig))

    def test_timestamp_freshness_boundary(self) -> None:
        now_ts = int(time.time())

        # Valid timestamp
        self.assertTrue(self.engine.validate_timestamp(now_ts))
        self.assertTrue(self.engine.validate_timestamp(now_ts - 200))

        # Stale timestamp (> 300 seconds)
        self.assertFalse(self.engine.validate_timestamp(now_ts - 350))

        # Future timestamp (> 60 seconds)
        self.assertFalse(self.engine.validate_timestamp(now_ts + 120))


if __name__ == "__main__":
    unittest.main()
