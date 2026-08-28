"""
Concurrency & Linearizability test suite for S01.7 Budget Engine.
"""

import concurrent.futures
import unittest

from apps.api.domain.budget_engine import BudgetEngine
from apps.api.domain.types import Currency


class TestBudgetEngineConcurrency(unittest.TestCase):
    """Exhaustive multi-threaded concurrency and race condition test suite for S01.7."""

    def setUp(self) -> None:
        self.engine = BudgetEngine()
        self.mandate_id = "mandate-conc-100"
        self.currency = Currency.INR
        self.daily_limit_paise = 10000  # ₹100
        self.engine.register_budget(
            mandate_id=self.mandate_id,
            daily_limit_paise=self.daily_limit_paise,
            currency=self.currency,
        )

    # ------------------------------------------------------------------
    # 1. Double-Spend Race (2 Competitors for > 50% Budget)
    # ------------------------------------------------------------------

    def test_double_spend_competing_threads_prevents_overspend(self) -> None:
        # Limit = 10,000 paise. Thread A = 7,000, Thread B = 7,000
        def _attempt_reservation(tx_id: str) -> bool:
            res = self.engine.reserve(
                mandate_id=self.mandate_id,
                transaction_id=tx_id,
                amount_paise=7000,
                currency=self.currency,
            )
            return res.valid

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(_attempt_reservation, "tx-a")
            f2 = executor.submit(_attempt_reservation, "tx-b")
            r1, r2 = f1.result(), f2.result()

        # Exactly ONE must succeed, ONE must fail!
        self.assertTrue(r1 ^ r2)

        budget = self.engine.get_budget(self.mandate_id)
        self.assertIsNotNone(budget)
        assert budget is not None
        self.assertEqual(budget.reserved_paise, 7000)
        self.assertEqual(budget.available_paise, 3000)
        self.assertLessEqual(budget.spent_paise + budget.reserved_paise, budget.daily_limit_paise)

    # ------------------------------------------------------------------
    # 2. 25 Concurrent Threads Over-subscribing Budget
    # ------------------------------------------------------------------

    def test_25_concurrent_reservations_linearizable_spending(self) -> None:
        # Limit = 10,000. 25 threads request 1,000 paise each (total 25,000 paise)
        def _worker(i: int) -> bool:
            res = self.engine.reserve(
                mandate_id=self.mandate_id,
                transaction_id=f"tx-worker-{i}",
                amount_paise=1000,
                currency=self.currency,
            )
            return res.valid

        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(_worker, i) for i in range(25)]
            results = [f.result() for f in futures]

        successful_count = sum(1 for r in results if r)
        failed_count = sum(1 for r in results if not r)

        # Exactly 10 reservations must succeed, 15 fail
        self.assertEqual(successful_count, 10)
        self.assertEqual(failed_count, 15)

        budget = self.engine.get_budget(self.mandate_id)
        assert budget is not None
        self.assertEqual(budget.reserved_paise, 10000)
        self.assertEqual(budget.available_paise, 0)

    # ------------------------------------------------------------------
    # 3. Concurrent Commit Operations
    # ------------------------------------------------------------------

    def test_concurrent_commits(self) -> None:
        res_ids = []
        for i in range(5):
            res = self.engine.reserve(
                mandate_id=self.mandate_id,
                transaction_id=f"tx-commit-{i}",
                amount_paise=2000,
                currency=self.currency,
            )
            assert res.reservation is not None
            res_ids.append(res.reservation.reservation_id)

        def _commit_worker(r_id: str) -> bool:
            try:
                self.engine.commit(mandate_id=self.mandate_id, reservation_id=r_id)
                return True
            except Exception:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(_commit_worker, r_id) for r_id in res_ids]
            results = [f.result() for f in futures]

        self.assertTrue(all(results))

        budget = self.engine.get_budget(self.mandate_id)
        assert budget is not None
        self.assertEqual(budget.reserved_paise, 0)
        self.assertEqual(budget.spent_paise, 10000)

    # ------------------------------------------------------------------
    # 4. Concurrent Double-Commit Race
    # ------------------------------------------------------------------

    def test_concurrent_double_commit_same_reservation_id(self) -> None:
        res = self.engine.reserve(
            mandate_id=self.mandate_id,
            transaction_id="tx-double-commit-race",
            amount_paise=5000,
            currency=self.currency,
        )
        assert res.reservation is not None
        res_id = res.reservation.reservation_id

        def _commit_same() -> bool:
            try:
                self.engine.commit(mandate_id=self.mandate_id, reservation_id=res_id)
                return True
            except ValueError:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_commit_same) for _ in range(10)]
            results = [f.result() for f in futures]

        # Exactly 1 thread must succeed, 9 must fail!
        self.assertEqual(sum(1 for r in results if r), 1)
        self.assertEqual(sum(1 for r in results if not r), 9)

        budget = self.engine.get_budget(self.mandate_id)
        assert budget is not None
        self.assertEqual(budget.reserved_paise, 0)
        self.assertEqual(budget.spent_paise, 5000)

    # ------------------------------------------------------------------
    # 5. Concurrent Double-Release Race
    # ------------------------------------------------------------------

    def test_concurrent_double_release_same_reservation_id(self) -> None:
        res = self.engine.reserve(
            mandate_id=self.mandate_id,
            transaction_id="tx-double-release-race",
            amount_paise=5000,
            currency=self.currency,
        )
        assert res.reservation is not None
        res_id = res.reservation.reservation_id

        def _release_same() -> bool:
            try:
                self.engine.release(mandate_id=self.mandate_id, reservation_id=res_id)
                return True
            except ValueError:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_release_same) for _ in range(10)]
            results = [f.result() for f in futures]

        # Exactly 1 thread must succeed, 9 must fail!
        self.assertEqual(sum(1 for r in results if r), 1)
        self.assertEqual(sum(1 for r in results if not r), 9)

        budget = self.engine.get_budget(self.mandate_id)
        assert budget is not None
        self.assertEqual(budget.reserved_paise, 0)
        self.assertEqual(budget.spent_paise, 0)
        self.assertEqual(budget.available_paise, 10000)


if __name__ == "__main__":
    unittest.main()
