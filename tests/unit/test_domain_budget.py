"""
Unit tests for DailyBudget & BudgetReservation data contracts and budget engine.
"""

import unittest
from datetime import datetime, timedelta, timezone

from apps.api.domain.budget import (
    BudgetInsufficientError,
    BudgetReservation,
    DailyBudget,
)
from apps.api.domain.budget_engine import (
    assert_can_reserve,
    commit_reservation,
    release_reservation,
    reserve_budget,
)
from apps.api.domain.types import Currency


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestDomainBudget(unittest.TestCase):
    """Test budget accounting, atomic reservation checks, commits, and releases."""

    def setUp(self) -> None:
        self.budget = DailyBudget(
            mandate_id="mandate-1",
            currency=Currency.INR,
            date_utc="2026-08-26",
            daily_limit_paise=500000,  # ₹5,000
            spent_paise=100000,  # ₹1,000
            reserved_paise=100000,  # ₹1,000
        )

    def test_derived_available_paise(self) -> None:
        # Available = 500000 - 100000 - 100000 = 300000 paise (₹3,000)
        self.assertEqual(self.budget.available_paise, 300000)

    def test_assert_can_reserve_success(self) -> None:
        # Reserving ₹2,000 (200000 paise) should succeed
        assert_can_reserve(self.budget, 200000)

    def test_assert_can_reserve_insufficient_raises(self) -> None:
        # Reserving ₹3,500 (350000 paise > available 300000) should raise
        with self.assertRaises(BudgetInsufficientError):
            assert_can_reserve(self.budget, 350000)

    def test_with_reservation_returns_new_budget(self) -> None:
        new_budget = reserve_budget(self.budget, 150000)
        self.assertEqual(new_budget.reserved_paise, 250000)
        self.assertEqual(new_budget.available_paise, 150000)
        # Original is unchanged (immutable)
        self.assertEqual(self.budget.reserved_paise, 100000)

    def test_commit_and_release(self) -> None:
        # Commit ₹500
        committed_budget = commit_reservation(self.budget, 50000)
        self.assertEqual(committed_budget.reserved_paise, 50000)
        self.assertEqual(committed_budget.spent_paise, 150000)

        # Release ₹500
        released_budget = release_reservation(self.budget, 50000)
        self.assertEqual(released_budget.reserved_paise, 50000)
        self.assertEqual(released_budget.spent_paise, 100000)

    def test_reservation_expiry(self) -> None:
        now = _utc_now()
        res = BudgetReservation(
            transaction_id="tx-1",
            mandate_id="mandate-1",
            amount_paise=100000,
            currency=Currency.INR,
            expires_at=now + timedelta(minutes=5),
        )
        self.assertFalse(res.is_expired(now))
        self.assertTrue(res.is_expired(now + timedelta(minutes=6)))


if __name__ == "__main__":
    unittest.main()
