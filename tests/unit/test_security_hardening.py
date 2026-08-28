"""
S03.3 — Security Hardening Unit Test Suite.

Tests SlidingWindowRateLimiter, secret redactor, posture evaluation, and offline receipt verifier.
"""

import unittest

from agent.security.engine import SecurityHardeningManager
from agent.security.errors import HardeningError, HardeningErrorCode
from agent.security.types import RateLimitRequest
from apps.api.domain.security_hardening import SecurityHardeningEngine, SlidingWindowRateLimiter


class TestSecurityHardeningUnit(unittest.TestCase):
    """Unit test cases for Security Hardening Engine & Manager."""

    def setUp(self) -> None:
        self.engine = SecurityHardeningEngine()
        self.manager = SecurityHardeningManager()

    def test_sliding_window_rate_limiter_allow_and_block(self) -> None:
        limiter = SlidingWindowRateLimiter()
        req = RateLimitRequest(
            identifier="127.0.0.1", action="test", max_requests=3, window_seconds=60
        )

        r1 = limiter.check_rate_limit(req)
        self.assertTrue(r1.allowed)
        self.assertEqual(r1.current_count, 1)

        r2 = limiter.check_rate_limit(req)
        self.assertTrue(r2.allowed)
        self.assertEqual(r2.current_count, 2)

        r3 = limiter.check_rate_limit(req)
        self.assertTrue(r3.allowed)
        self.assertEqual(r3.current_count, 3)

        r4 = limiter.check_rate_limit(req)
        self.assertFalse(r4.allowed)
        self.assertGreater(r4.retry_after_seconds, 0)

    def test_secret_redaction(self) -> None:
        payload = {
            "merchant_id": "m_123",
            "razorpay_secret": "rzp_sec_999",
            "nested": {
                "bearer_token": "eyJhbGciOi...",
                "normal": "value",
            },
            "raw_key": "sk_live_123456",
        }

        redacted = self.engine.redact_sensitive_data(payload)
        self.assertEqual(redacted["merchant_id"], "m_123")
        self.assertEqual(redacted["razorpay_secret"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["bearer_token"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["normal"], "value")
        self.assertEqual(redacted["raw_key"], "[REDACTED_SECRET_TOKEN]")

    def test_posture_evaluation(self) -> None:
        posture = self.manager.get_posture()
        self.assertTrue(posture.fail_closed_mode_active)
        self.assertTrue(posture.database_persistence_healthy)
        self.assertTrue(posture.redis_cache_healthy)
        self.assertIn("FAIL_CLOSED_AUTHORIZATION_GATEWAY", posture.active_threat_mitigations)

    def test_forced_db_failure_fails_closed(self) -> None:
        self.engine.set_forced_persistence_failure(db_down=True)

        posture = self.engine.get_posture()
        self.assertFalse(posture.database_persistence_healthy)
        self.assertIn("FAIL_CLOSED_PERSISTENCE_MODE_ACTIVE", posture.active_threat_mitigations)

        req = RateLimitRequest(
            identifier="user1", action="execute", max_requests=10, window_seconds=60
        )
        with self.assertRaises(HardeningError) as ctx:
            self.engine.check_rate_limit(req)
        self.assertEqual(ctx.exception.code, HardeningErrorCode.DATABASE_FAIL_CLOSED)


if __name__ == "__main__":
    unittest.main()
