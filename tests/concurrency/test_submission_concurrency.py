"""
S03.4 — Submission Concurrency Test Suite.

Tests thread safety of SubmissionReadinessEngine under 20 and 50 parallel worker threads.
"""

import concurrent.futures
import unittest

from apps.api.domain.submission import SubmissionReadinessEngine


class TestSubmissionConcurrency(unittest.TestCase):
    """Concurrency test cases for S03.4 Submission Readiness."""

    def test_submission_readiness_concurrency_20_workers(self) -> None:
        engine = SubmissionReadinessEngine()
        results: list[bool] = []

        def worker() -> bool:
            st = engine.evaluate_submission_readiness()
            return st.is_submission_ready

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker) for _ in range(20)]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        self.assertEqual(len(results), 20)
        self.assertTrue(all(results))

    def test_benchmark_concurrency_50_workers(self) -> None:
        engine = SubmissionReadinessEngine()
        results: list[float] = []

        def worker() -> float:
            bm = engine.run_performance_benchmarks()
            return bm.rate_limiter_throughput_ops

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(worker) for _ in range(50)]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        self.assertEqual(len(results), 50)
        self.assertTrue(all(r > 0.0 for r in results))


if __name__ == "__main__":
    unittest.main()
