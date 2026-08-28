"""
S04.4 — Concurrency Test Suite for Crash Consistency, Recovery & Reconciliation.

Verifies thread-safe crash audit scans, concurrent reconciliation attempts,
and parallel budget recovery under high worker thread contention.
"""

from __future__ import annotations

import concurrent.futures
import unittest
from datetime import datetime, timezone

from apps.api.domain.budget_engine import BudgetEngine
from apps.api.domain.reconciliation import RecoveryReconciliationEngine
from apps.api.domain.types import Currency, TransactionState


class TestS044RecoveryConcurrency(unittest.TestCase):
    """Concurrency tests for S04.4 Crash Recovery Engine."""

    def setUp(self) -> None:
        self.reconciliation_engine = RecoveryReconciliationEngine()
        self.budget_engine = BudgetEngine()

    def test_50_worker_concurrent_stale_transaction_audits(self) -> None:
        """Verify 50 parallel worker threads scanning transactions for stale state execute safely."""
        now = datetime.now(timezone.utc)
        transactions = [
            {
                "transaction_id": f"tx_stale_{i}",
                "mandate_id": f"m_{i}",
                "merchant_id": f"merch_{i}",
                "amount_paise": 1000,
                "state": TransactionState.EXECUTING.value,
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
            for i in range(20)
        ]

        def scan_stale(worker_id: int) -> int:
            stale = self.reconciliation_engine.audit_stale_transactions(
                transactions, timeout_seconds=300, at=now
            )
            return len(stale)

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(scan_stale, i) for i in range(50)]
            outcomes = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.assertTrue(all(count == 20 for count in outcomes))

    def test_50_worker_concurrent_budget_reconciliation(self) -> None:
        """Verify 50 parallel workers attempting budget recovery achieve exact-once release."""
        m_id = "mandate_conc_rec"
        self.budget_engine.register_budget(m_id, daily_limit_paise=10000, currency=Currency.INR)
        self.budget_engine.reserve(m_id, "tx_conc_failed", 5000, Currency.INR)

        transactions = [
            {
                "transaction_id": "tx_conc_failed",
                "mandate_id": m_id,
                "amount_paise": 5000,
                "state": TransactionState.FAILURE.value,
            }
        ]

        def recover_budget(worker_id: int) -> bool:
            orphaned = self.reconciliation_engine.audit_budget_reservations(
                self.budget_engine, transactions
            )
            return len(orphaned) > 0 and orphaned[0].released

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(recover_budget, i) for i in range(50)]
            outcomes = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Exactly 1 worker will successfully perform the release; others find 0 reserved_paise left
        self.assertEqual(sum(1 for o in outcomes if o), 1)
        b = self.budget_engine.get_budget(m_id)
        self.assertIsNotNone(b)
        if b is not None:
            self.assertEqual(b.reserved_paise, 0)


if __name__ == "__main__":
    unittest.main()
