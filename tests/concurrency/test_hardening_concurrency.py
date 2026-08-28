"""
S03.3 — Security Hardening Concurrency Test Suite.

Tests thread safety of SlidingWindowRateLimiter and SecurityHardeningEngine
under 20 and 50 parallel worker threads.
"""

import concurrent.futures
import unittest

from agent.security.types import RateLimitRequest
from apps.api.domain.security_hardening import SecurityHardeningEngine, SlidingWindowRateLimiter


class TestHardeningConcurrency(unittest.TestCase):
    """Concurrency test cases for S03.3 Security Hardening."""

    def test_rate_limiter_concurrency_20_workers(self) -> None:
        limiter = SlidingWindowRateLimiter()
        req = RateLimitRequest(
            identifier="concurrent_user_20",
            action="execute",
            max_requests=10,
            window_seconds=60,
        )

        results: list[bool] = []

        def worker() -> bool:
            res = limiter.check_rate_limit(req)
            return res.allowed

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker) for _ in range(20)]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        allowed_count = sum(1 for r in results if r)
        blocked_count = sum(1 for r in results if not r)

        self.assertEqual(allowed_count, 10)
        self.assertEqual(blocked_count, 10)

    def test_rate_limiter_concurrency_50_workers(self) -> None:
        engine = SecurityHardeningEngine()
        req = RateLimitRequest(
            identifier="concurrent_user_50",
            action="checkout",
            max_requests=15,
            window_seconds=60,
        )

        results: list[bool] = []

        def worker() -> bool:
            res = engine.check_rate_limit(req)
            return res.allowed

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(worker) for _ in range(50)]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        allowed_count = sum(1 for r in results if r)
        blocked_count = sum(1 for r in results if not r)

        self.assertEqual(allowed_count, 15)
        self.assertEqual(blocked_count, 35)


if __name__ == "__main__":
    unittest.main()
