"""
Unit, Security & Boundary tests for S01.7 Budget Engine.
"""

import unittest
from datetime import datetime, timezone

from apps.api.domain.budget_engine import BudgetEngine
from apps.api.domain.types import BudgetState, Currency, PolicyDecision, RejectionReason


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestBudgetEngineUnit(unittest.TestCase):
    """Exhaustive unit test suite for S01.7 BudgetEngine."""

    def setUp(self) -> None:
        self.engine = BudgetEngine()
        self.mandate_id = "mandate-uuid-700"
        self.currency = Currency.INR
        self.daily_limit_paise = 10000  # ₹100 daily limit
        self.engine.register_budget(
            mandate_id=self.mandate_id,
            daily_limit_paise=self.daily_limit_paise,
            currency=self.currency,
        )

    # ------------------------------------------------------------------
    # 1. Single-Threaded Reservation & Accounting
    # ------------------------------------------------------------------

    def test_successful_budget_reservation(self) -> None:
        res = self.engine.reserve(
            mandate_id=self.mandate_id,
            transaction_id="tx-1",
            amount_paise=4000,  # ₹40
            currency=self.currency,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.decision, PolicyDecision.ALLOW)
        self.assertEqual(res.requested_paise, 4000)
        self.assertEqual(res.available_paise, 6000)
        self.assertIsNotNone(res.reservation)
        assert res.reservation is not None
        self.assertEqual(res.reservation.state, BudgetState.RESERVED)

        # Check budget state
        budget = self.engine.get_budget(self.mandate_id)
        self.assertIsNotNone(budget)
        assert budget is not None
        self.assertEqual(budget.spent_paise, 0)
        self.assertEqual(budget.reserved_paise, 4000)
        self.assertEqual(budget.available_paise, 6000)

    def test_overspend_reservation_rejected(self) -> None:
        # Request 10,001 paise against 10,000 limit
        res = self.engine.reserve(
            mandate_id=self.mandate_id,
            transaction_id="tx-overspend",
            amount_paise=10001,
            currency=self.currency,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.decision, PolicyDecision.REJECT)
        self.assertEqual(res.rejection_reason, RejectionReason.BUDGET_EXCEEDED)

        # Budget state remains untouched
        budget = self.engine.get_budget(self.mandate_id)
        assert budget is not None
        self.assertEqual(budget.reserved_paise, 0)

    # ------------------------------------------------------------------
    # 2. Exact Boundary Tests
    # ------------------------------------------------------------------

    def test_exact_boundary_reservation_allows_and_rejects_plus_one(self) -> None:
        # Register budget: limit = 10,000, spent = 3,000, reserved = 2,000 -> Available = 5,000
        engine = BudgetEngine()
        engine.register_budget(
            mandate_id="mandate-boundary",
            daily_limit_paise=10000,
            currency=Currency.INR,
            spent_paise=3000,
            reserved_paise=2000,
        )

        # 1. Exact boundary request = 5,000 paise -> ALLOW
        res_exact = engine.reserve(
            mandate_id="mandate-boundary",
            transaction_id="tx-boundary-exact",
            amount_paise=5000,
            currency=Currency.INR,
        )
        self.assertTrue(res_exact.valid)
        self.assertEqual(res_exact.available_paise, 0)

        # 2. Boundary + 1 request = 1 paise against 0 available -> REJECT
        res_plus_one = engine.reserve(
            mandate_id="mandate-boundary",
            transaction_id="tx-boundary-plus-one",
            amount_paise=1,
            currency=Currency.INR,
        )
        self.assertFalse(res_plus_one.valid)
        self.assertEqual(res_plus_one.rejection_reason, RejectionReason.BUDGET_EXCEEDED)

    # ------------------------------------------------------------------
    # 3. Non-Positive Values & Currency Integrity
    # ------------------------------------------------------------------

    def test_zero_and_negative_amounts_rejected(self) -> None:
        for bad_amount in [0, -1, -5000]:
            res = self.engine.reserve(
                mandate_id=self.mandate_id,
                transaction_id=f"tx-bad-{bad_amount}",
                amount_paise=bad_amount,
                currency=self.currency,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.rejection_reason, RejectionReason.INVALID_AMOUNT)

    def test_currency_mismatch_rejected(self) -> None:
        res = self.engine.reserve(
            mandate_id=self.mandate_id,
            transaction_id="tx-currency",
            amount_paise=1000,
            currency=Currency.USD,  # USD vs INR mandate
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.rejection_reason, RejectionReason.BUDGET_CURRENCY_MISMATCH)

    # ------------------------------------------------------------------
    # 4. Commit Semantics & Illegal Transitions
    # ------------------------------------------------------------------

    def test_commit_reservation_success(self) -> None:
        res = self.engine.reserve(
            mandate_id=self.mandate_id,
            transaction_id="tx-commit",
            amount_paise=3000,
            currency=self.currency,
        )
        assert res.reservation is not None
        res_id = res.reservation.reservation_id

        # Commit reservation
        committed_res = self.engine.commit(mandate_id=self.mandate_id, reservation_id=res_id)
        self.assertEqual(committed_res.state, BudgetState.COMMITTED)

        budget = self.engine.get_budget(self.mandate_id)
        assert budget is not None
        self.assertEqual(budget.reserved_paise, 0)
        self.assertEqual(budget.spent_paise, 3000)
        self.assertEqual(budget.available_paise, 7000)

    def test_double_commit_fails_closed(self) -> None:
        res = self.engine.reserve(
            mandate_id=self.mandate_id,
            transaction_id="tx-double-commit",
            amount_paise=3000,
            currency=self.currency,
        )
        assert res.reservation is not None
        res_id = res.reservation.reservation_id

        self.engine.commit(mandate_id=self.mandate_id, reservation_id=res_id)

        with self.assertRaises(ValueError) as ctx:
            self.engine.commit(mandate_id=self.mandate_id, reservation_id=res_id)
        self.assertIn("already COMMITTED", str(ctx.exception))

    # ------------------------------------------------------------------
    # 5. Release Semantics & Illegal Transitions
    # ------------------------------------------------------------------

    def test_release_reservation_success(self) -> None:
        res = self.engine.reserve(
            mandate_id=self.mandate_id,
            transaction_id="tx-release",
            amount_paise=4000,
            currency=self.currency,
        )
        assert res.reservation is not None
        res_id = res.reservation.reservation_id

        released_res = self.engine.release(mandate_id=self.mandate_id, reservation_id=res_id)
        self.assertEqual(released_res.state, BudgetState.RELEASED)

        budget = self.engine.get_budget(self.mandate_id)
        assert budget is not None
        self.assertEqual(budget.reserved_paise, 0)
        self.assertEqual(budget.spent_paise, 0)  # Spent must NOT increase!
        self.assertEqual(budget.available_paise, 10000)

    def test_double_release_fails_closed(self) -> None:
        res = self.engine.reserve(
            mandate_id=self.mandate_id,
            transaction_id="tx-double-release",
            amount_paise=4000,
            currency=self.currency,
        )
        assert res.reservation is not None
        res_id = res.reservation.reservation_id

        self.engine.release(mandate_id=self.mandate_id, reservation_id=res_id)

        with self.assertRaises(ValueError) as ctx:
            self.engine.release(mandate_id=self.mandate_id, reservation_id=res_id)
        self.assertIn("already RELEASED", str(ctx.exception))

    def test_commit_after_release_fails_closed(self) -> None:
        res = self.engine.reserve(
            mandate_id=self.mandate_id,
            transaction_id="tx-commit-after-release",
            amount_paise=2000,
            currency=self.currency,
        )
        assert res.reservation is not None
        res_id = res.reservation.reservation_id

        self.engine.release(mandate_id=self.mandate_id, reservation_id=res_id)

        with self.assertRaises(ValueError) as ctx:
            self.engine.commit(mandate_id=self.mandate_id, reservation_id=res_id)
        self.assertIn("Cannot commit RELEASED reservation", str(ctx.exception))

    def test_release_after_commit_fails_closed(self) -> None:
        res = self.engine.reserve(
            mandate_id=self.mandate_id,
            transaction_id="tx-release-after-commit",
            amount_paise=2000,
            currency=self.currency,
        )
        assert res.reservation is not None
        res_id = res.reservation.reservation_id

        self.engine.commit(mandate_id=self.mandate_id, reservation_id=res_id)

        with self.assertRaises(ValueError) as ctx:
            self.engine.release(mandate_id=self.mandate_id, reservation_id=res_id)
        self.assertIn("Cannot release COMMITTED reservation", str(ctx.exception))

    # ------------------------------------------------------------------
    # 6. S01.5 Aggregator Integration
    # ------------------------------------------------------------------

    def test_to_security_control_outcome_conversion(self) -> None:
        res = self.engine.reserve(
            mandate_id=self.mandate_id,
            transaction_id="tx-s015",
            amount_paise=1000,
            currency=self.currency,
        )
        outcome = res.to_security_control_outcome()
        self.assertEqual(outcome.control_name, "BUDGET")
        self.assertTrue(outcome.passed)
        self.assertEqual(outcome.decision, PolicyDecision.ALLOW)


if __name__ == "__main__":
    unittest.main()
