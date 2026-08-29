"""
M14 Integration Tests — Multi-Category Rate Limiting & Distributed Abuse Controls
"""

import unittest
from apps.api.security.rate_limiter import RateLimiter, RateLimitExceededError


class TestM14RateLimitSecurity(unittest.TestCase):
    """Test category rate limits, identity key sliding window, and fail-closed abuse control."""

    def setUp(self) -> None:
        self.rate_limiter = RateLimiter(requests_per_minute=100, window_seconds=60)

    def test_auth_failures_category_rate_limit(self) -> None:
        key = "fp_rzp_test_attacker_ip"
        # Category AUTH_FAILURES has limit 5 req / 60s
        for _ in range(5):
            self.rate_limiter.check_rate_limit(key, category="AUTH_FAILURES")

        with self.assertRaises(RateLimitExceededError) as ctx:
            self.rate_limiter.check_rate_limit(key, category="AUTH_FAILURES")
        self.assertGreaterEqual(ctx.exception.retry_after_seconds, 1)

    def test_payment_execution_category_rate_limit(self) -> None:
        key = "fp_rzp_test_merchant_exec"
        # Category PAYMENT_EXECUTION has limit 20 req / 60s
        for _ in range(20):
            self.rate_limiter.check_rate_limit(key, category="PAYMENT_EXECUTION")

        with self.assertRaises(RateLimitExceededError):
            self.rate_limiter.check_rate_limit(key, category="PAYMENT_EXECUTION")

    def test_different_identities_are_isolated(self) -> None:
        key_a = "fp_rzp_merchant_a"
        key_b = "fp_rzp_merchant_b"

        for _ in range(5):
            self.rate_limiter.check_rate_limit(key_a, category="AUTH_FAILURES")

        # key_a is now rate-limited
        with self.assertRaises(RateLimitExceededError):
            self.rate_limiter.check_rate_limit(key_a, category="AUTH_FAILURES")

        # key_b is still allowed
        self.rate_limiter.check_rate_limit(key_b, category="AUTH_FAILURES")


if __name__ == "__main__":
    unittest.main()
