"""
Concurrency & Linearizability test suite for S01.8 Replay Protection Engine.
"""

import concurrent.futures
import unittest

from apps.api.domain.replay_engine import ReplayProtectionEngine


class TestReplayEngineConcurrency(unittest.TestCase):
    """Exhaustive multi-threaded concurrency and race condition test suite for S01.8."""

    def setUp(self) -> None:
        self.engine = ReplayProtectionEngine()
        self.mandate_id = "mandate-conc-800"
        self.transaction_id = "tx-conc-800"

    # ------------------------------------------------------------------
    # 1. 20 Concurrent Threads Submitting Same Replay Key
    # ------------------------------------------------------------------

    def test_20_concurrent_identical_requests_allows_exactly_one(self) -> None:
        def _attempt_replay() -> bool:
            res = self.engine.check_and_record(
                mandate_id=self.mandate_id,
                transaction_id=self.transaction_id,
            )
            return res.valid

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(_attempt_replay) for _ in range(20)]
            results = [f.result() for f in futures]

        successful_count = sum(1 for r in results if r)
        failed_count = sum(1 for r in results if not r)

        # Exactly 1 thread must succeed, 19 fail
        self.assertEqual(successful_count, 1)
        self.assertEqual(failed_count, 19)
        self.assertEqual(self.engine.record_count(), 1)

    # ------------------------------------------------------------------
    # 2. 50 Mixed Concurrent Requests Across 10 Unique Transaction IDs
    # ------------------------------------------------------------------

    def test_50_mixed_concurrent_requests_preserves_unique_successes(self) -> None:
        # 10 unique tx_ids, each submitted by 5 threads (total 50 requests)
        tx_ids = [f"tx-mixed-{i}" for i in range(10)]
        request_pool = tx_ids * 5  # 50 total tasks

        def _worker(tx_id: str) -> bool:
            res = self.engine.check_and_record(
                mandate_id=self.mandate_id,
                transaction_id=tx_id,
            )
            return res.valid

        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(_worker, tx_id) for tx_id in request_pool]
            results = [f.result() for f in futures]

        successful_count = sum(1 for r in results if r)
        failed_count = sum(1 for r in results if not r)

        # Exactly 10 unique transactions must succeed, 40 fail
        self.assertEqual(successful_count, 10)
        self.assertEqual(failed_count, 40)
        self.assertEqual(self.engine.record_count(), 10)


if __name__ == "__main__":
    unittest.main()
