"""
M14 Multi-Process Security Verification Tests
"""

import multiprocessing
import unittest
from apps.api.security.rate_limiter import RateLimiter, RateLimitExceededError


def _worker_attempt(key: str, category: str, result_queue: multiprocessing.Queue) -> None:
    limiter = RateLimiter(requests_per_minute=10, window_seconds=60)
    try:
        limiter.check_rate_limit(key, category=category)
        result_queue.put(True)
    except RateLimitExceededError:
        result_queue.put(False)


class TestM14MultiprocessSecurity(unittest.TestCase):
    """Verify security controls across multi-process worker pools."""

    def test_multiprocess_security_boundary(self) -> None:
        q: multiprocessing.Queue = multiprocessing.Queue()
        processes = []
        for _ in range(5):
            p = multiprocessing.Process(
                target=_worker_attempt, args=("fp_rzp_mp_test", "GENERAL_API", q)
            )
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

        results = []
        while not q.empty():
            results.append(q.get())

        self.assertEqual(len(results), 5)
        self.assertTrue(all(results))


if __name__ == "__main__":
    unittest.main()
