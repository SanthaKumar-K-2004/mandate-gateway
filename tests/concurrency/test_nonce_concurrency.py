"""
Concurrency & Linearizability test suite for S01.9 Nonce & Authorization Freshness Engine.
"""

import concurrent.futures
import unittest

from apps.api.domain.nonce_engine import NonceEngine


class TestNonceEngineConcurrency(unittest.TestCase):
    """Exhaustive multi-threaded concurrency and race condition test suite for S01.9."""

    def setUp(self) -> None:
        self.engine = NonceEngine()
        self.mandate_id = "mandate-conc-900"
        self.transaction_id = "tx-conc-900"

    # ------------------------------------------------------------------
    # 1. 20 Concurrent Threads Attempting to Consume the Same Nonce
    # ------------------------------------------------------------------

    def test_20_concurrent_consumption_attempts_allows_exactly_one(self) -> None:
        record = self.engine.issue_nonce(
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            ttl_seconds=300,
        )

        def _worker() -> bool:
            res = self.engine.validate_and_consume(
                nonce_value=record.nonce_value,
                mandate_id=self.mandate_id,
                transaction_id=self.transaction_id,
            )
            return res.valid

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(_worker) for _ in range(20)]
            results = [f.result() for f in futures]

        successful_count = sum(1 for r in results if r)
        failed_count = sum(1 for r in results if not r)

        # Exactly 1 thread must succeed, 19 fail
        self.assertEqual(successful_count, 1)
        self.assertEqual(failed_count, 19)

    # ------------------------------------------------------------------
    # 2. 50 Mixed Concurrent Requests Across 10 Unique Nonces
    # ------------------------------------------------------------------

    def test_50_mixed_concurrent_requests_preserves_unique_consumptions(self) -> None:
        records = [
            self.engine.issue_nonce(
                mandate_id=self.mandate_id,
                transaction_id=f"tx-mixed-{i}",
                ttl_seconds=300,
            )
            for i in range(10)
        ]
        nonce_pool = [r.nonce_value for r in records] * 5  # 50 total tasks (5 per nonce)

        def _worker(nonce_val: str) -> bool:
            rec = self.engine.get_nonce(nonce_val)
            tx_id = rec.transaction_id if rec else self.transaction_id
            res = self.engine.validate_and_consume(
                nonce_value=nonce_val,
                mandate_id=self.mandate_id,
                transaction_id=tx_id,
            )
            return res.valid

        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(_worker, nv) for nv in nonce_pool]
            results = [f.result() for f in futures]

        successful_count = sum(1 for r in results if r)
        failed_count = sum(1 for r in results if not r)

        # Exactly 10 unique nonces must be consumed, 40 fail
        self.assertEqual(successful_count, 10)
        self.assertEqual(failed_count, 40)


if __name__ == "__main__":
    unittest.main()
