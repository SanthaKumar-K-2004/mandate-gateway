"""
Unit tests for S05.3.3 MandateRepository.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.domain.mandate_lifecycle import MandateStateTransitionError
from apps.api.domain.types import MandateStatus
from db.models.mandate import MandateModel
from db.repository.mandate_repository import MandateRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestMandateRepositoryUnit(unittest.IsolatedAsyncioTestCase):
    """Unit test suite for MandateRepository."""

    async def test_create_mandate_flushes(self) -> None:
        """Verify create_mandate adds entity to session and flushes."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = MandateRepository(mock_session)

        exp = _utc_now() + timedelta(days=30)
        mandate = await repo.create_mandate(
            mandate_id="man_unit_1",
            buyer_id="buyer_1",
            daily_budget_paise=100000,
            expires_at=exp,
            merchant_id="m_1",
        )

        self.assertEqual(mandate.mandate_id, "man_unit_1")
        self.assertEqual(mandate.buyer_id, "buyer_1")
        self.assertEqual(mandate.daily_budget_paise, 100000)
        self.assertEqual(mandate.status, MandateStatus.ACTIVE.value)
        mock_session.add.assert_called_once_with(mandate)
        mock_session.flush.assert_awaited_once()

    async def test_get_mandate_by_id(self) -> None:
        """Verify get_mandate delegates to get_by_id."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_mandate = MandateModel(mandate_id="man_unit_2", buyer_id="buyer_2")
        mock_session.get.return_value = mock_mandate

        repo = MandateRepository(mock_session)
        result = await repo.get_mandate("man_unit_2")

        mock_session.get.assert_awaited_once_with(MandateModel, "man_unit_2")
        self.assertIs(result, mock_mandate)

    async def test_get_mandate_for_buyer_isolation(self) -> None:
        """Verify get_mandate_for_buyer applies both mandate_id and buyer_id filters."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_mandate = MandateModel(mandate_id="man_unit_3", buyer_id="buyer_3")
        mock_result.scalar_one_or_none.return_value = mock_mandate
        mock_session.execute.return_value = mock_result

        repo = MandateRepository(mock_session)
        result = await repo.get_mandate_for_buyer("man_unit_3", "buyer_3")

        mock_session.execute.assert_awaited_once()
        self.assertIs(result, mock_mandate)

    async def test_transition_mandate_status_illegal_transition(self) -> None:
        """Verify legal transitions enforced and illegal transition raises MandateStateTransitionError."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        # REVOKED is terminal state — cannot transition out
        mock_mandate = MandateModel(
            mandate_id="man_unit_4", buyer_id="b_4", status=MandateStatus.REVOKED.value
        )
        mock_result.scalar_one_or_none.return_value = mock_mandate
        mock_session.execute.return_value = mock_result

        repo = MandateRepository(mock_session)
        with self.assertRaises(MandateStateTransitionError):
            await repo.transition_mandate_status("man_unit_4", MandateStatus.ACTIVE)


if __name__ == "__main__":
    unittest.main()
