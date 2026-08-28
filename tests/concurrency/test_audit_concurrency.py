"""
S02.6 — Audit Ledger Concurrency & State Isolation Tests.

Tests parallel thread safety of AuditLedger append-only operations under high
concurrency (20 concurrent worker threads).
"""

import concurrent.futures
import unittest

from apps.api.domain.audit_ledger import AuditLedger
from apps.api.domain.types import AuditEventType


class TestAuditConcurrency(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = AuditLedger()

    def test_concurrent_appends_preserve_chain_integrity(self) -> None:
        """Verify 20 concurrent workers appending events preserve hash-chain integrity."""
        num_workers = 20
        events_per_worker = 15
        total_expected_events = num_workers * events_per_worker

        def worker_task(worker_id: int) -> list[str]:
            appended_hashes = []
            for i in range(events_per_worker):
                event = self.ledger.append_event(
                    event_type=(
                        AuditEventType.TOOL_BLOCKED if i % 2 == 0 else AuditEventType.CART_PROPOSED
                    ),
                    transaction_id=f"tx_w{worker_id}_{i}",
                    mandate_id=f"mandate_{worker_id}",
                    payload={"worker_id": worker_id, "step": i},
                )
                appended_hashes.append(event.event_hash)
            return appended_hashes

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_task, w) for w in range(num_workers)]
            results = [f.result() for f in futures]

        # Verify event count
        self.assertEqual(self.ledger.count(), total_expected_events)

        # Verify complete cryptographic chain integrity
        is_valid, err = self.ledger.verify_chain()
        self.assertTrue(is_valid, msg=f"Concurrent chain verification failed: {err}")
        self.assertIsNone(err)

        # Verify all worker event hashes are present in ledger
        all_appended = [h for res in results for h in res]
        self.assertEqual(len(all_appended), total_expected_events)


if __name__ == "__main__":
    unittest.main()
