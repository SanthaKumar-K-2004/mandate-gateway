"""
S03.3 — Security Hardening & Fail-Closed Security Test Suite.

Tests fail-closed modes, rate limiter denial of service defense, secret leakage prevention,
and tamper rejection on offline receipts.
"""

import unittest

from agent.security.engine import SecurityHardeningManager
from agent.security.errors import HardeningError, HardeningErrorCode
from agent.security.types import RateLimitRequest, ReceiptVerifyRequest
from apps.api.domain.security_hardening import SecurityHardeningEngine


class TestHardeningSecurity(unittest.TestCase):
    """Security and fail-closed test cases for S03.3."""

    def setUp(self) -> None:
        self.engine = SecurityHardeningEngine()
        self.manager = SecurityHardeningManager()

    def test_rate_limit_mitigates_dos_flooding(self) -> None:
        req = RateLimitRequest(
            identifier="attacker_ip_10.0.0.1",
            action="execute_intent",
            max_requests=5,
            window_seconds=60,
        )

        for _ in range(5):
            res = self.engine.check_rate_limit(req)
            self.assertTrue(res.allowed)

        # 6th request must be blocked
        blocked_res = self.engine.check_rate_limit(req)
        self.assertFalse(blocked_res.allowed)
        self.assertEqual(blocked_res.current_count, 5)
        self.assertGreater(blocked_res.retry_after_seconds, 0.0)

    def test_database_failure_fails_closed_completely(self) -> None:
        self.engine.set_forced_persistence_failure(db_down=True)

        req = RateLimitRequest(
            identifier="user1", action="execute", max_requests=10, window_seconds=60
        )
        with self.assertRaises(HardeningError) as ctx:
            self.engine.check_rate_limit(req)
        self.assertEqual(ctx.exception.code, HardeningErrorCode.DATABASE_FAIL_CLOSED)

        v_req = ReceiptVerifyRequest(
            receipt_id="rcpt_123",
            transaction_id="tx_123",
            mandate_id="man_123",
            merchant_id="mer_123",
            policy_version=1,
            cart_hash="hash_123",
            amount_paise=1000,
            decision="ALLOW",
            execution_tool="create_order",
            execution_reference="ref_123",
            audit_hash="ahash_123",
            signature="sig_123",
        )
        with self.assertRaises(HardeningError) as ctx2:
            self.engine.verify_receipt_cryptographic_offline(v_req)
        self.assertEqual(ctx2.exception.code, HardeningErrorCode.DATABASE_FAIL_CLOSED)

    def test_invalid_receipt_signature_fails_offline_verification(self) -> None:
        v_req = ReceiptVerifyRequest(
            receipt_id="rcpt_fake",
            transaction_id="tx_fake",
            mandate_id="man_fake",
            merchant_id="mer_fake",
            policy_version=1,
            cart_hash="f" * 64,
            amount_paise=5000,
            decision="ALLOW",
            execution_tool="create_order",
            execution_reference="ref_fake",
            audit_hash="ahash_fake",
            signature="invalid_ed25519_signature_hex_data",
        )

        res = self.engine.verify_receipt_cryptographic_offline(v_req)
        self.assertFalse(res.valid)
        self.assertFalse(res.signature_valid)


if __name__ == "__main__":
    unittest.main()
