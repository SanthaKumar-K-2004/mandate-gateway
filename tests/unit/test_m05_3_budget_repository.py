"""
Unit tests for S05.3.5 BudgetRepository.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.domain.types import BudgetState
from db.models.mandate import MandateModel
from db.repository.budget_repository import BudgetRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestBudgetRepositoryUnit(unittest.IsolatedAsyncioTestCase):
    """Unit test suite for BudgetRepository."""

    async def test_create_reservation_flushes(self) -> None:
        """Verify create_reservation adds model and flushes session."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = BudgetRepository(mock_session)

        res = await repo.create_reservation(
            reservation_id="res_unit_1",
            mandate_id="man_1",
            transaction_id="tx_1",
            requested_paise=1000,
            reserved_paise=1000,
        )

        self.assertEqual(res.reservation_id, "res_unit_1")
        self.assertEqual(res.state, BudgetState.RESERVED.value)
        mock_session.add.assert_called_once_with(res)
        mock_session.flush.assert_awaited_once()

    async def test_negative_amounts_rejected(self) -> None:
        """Verify negative requested_paise or reserved_paise raises ValueError."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = BudgetRepository(mock_session)

        with self.assertRaises(ValueError):
            await repo.create_reservation("res_1", "m_1", "tx_1", -100, 100)

        with self.assertRaises(ValueError):
            await repo.create_reservation("res_2", "m_1", "tx_2", 100, -100)

    async def test_reserve_budget_atomically_insufficient_budget(self) -> None:
        """Verify reserve_budget_atomically raises ValueError when limit is exceeded."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result_mandate = MagicMock()
        mock_mandate = MandateModel(
            mandate_id="man_limit",
            daily_budget_paise=10000,  # Limit is 10,000 paise
        )
        mock_result_mandate.scalar_one_or_none.return_value = mock_mandate

        mock_result_sum = MagicMock()
        mock_result_sum.scalar.return_value = 8000  # Already reserved 8,000 paise

        mock_session.execute.side_effect = [mock_result_mandate, mock_result_sum]

        repo = BudgetRepository(mock_session)
        with self.assertRaises(ValueError) as ctx:
            await repo.reserve_budget_atomically(
                reservation_id="res_over",
                mandate_id="man_limit",
                transaction_id="tx_over",
                requested_paise=3000,  # 8000 + 3000 > 10000 -> Overspend!
            )
        self.assertIn("Budget insufficient", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
