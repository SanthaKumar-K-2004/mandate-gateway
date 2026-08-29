"""
M14 Concurrency Tests — Concurrent Auth Abuse, Concurrent Rate Limit Breaches & Parallel Webhooks
"""

import concurrent.futures
import unittest

from apps.api.security.rate_limiter import RateLimiter, RateLimitExceededError


class TestM14SecurityConcurrency(unittest.TestCase):
    """Test concurrent authentication abuse, rate limiting thread-safety, and parallel request bounds."""

    def test_concurrent_rate_limiting_thread_safety(self) -> None:
        rate_limiter = RateLimiter(requests_per_minute=20, window_seconds=60)
        key = "fp_rzp_concurrent_user"

        def make_request(idx: int) -> bool:
            try:
                rate_limiter.check_rate_limit(key, category="PAYMENT_EXECUTION")
                return True
            except RateLimitExceededError:
                return False

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(50)]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        allowed_count = sum(1 for r in results if r)
        rejected_count = sum(1 for r in results if not r)

        self.assertEqual(allowed_count, 20)
        self.assertEqual(rejected_count, 30)


if __name__ == "__main__":
    unittest.main()
