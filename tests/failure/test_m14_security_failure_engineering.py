"""
M14 Failure Engineering Tests — System Resilience & Security Fail-Closed Invariants
"""

import unittest
from unittest.mock import patch

from apps.api.security.rate_limiter import RateLimiter


class TestM14SecurityFailureEngineering(unittest.TestCase):
    """Test failure mode resilience and fail-closed security invariants under error conditions."""

    def test_rate_limiter_fail_closed_under_exception(self) -> None:
        limiter = RateLimiter(requests_per_minute=10, window_seconds=60)
        with patch.object(limiter, "is_allowed", side_effect=RuntimeError("Redis connection lost")):
            with self.assertRaises(RuntimeError):
                limiter.check_rate_limit("fp_rzp_test_key")


if __name__ == "__main__":
    unittest.main()
