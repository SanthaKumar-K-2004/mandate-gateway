"""
Unit tests for S05.3.6.1 StepUpRepository.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.domain.step_up import StepUpChallengeStatus
from db.models.step_up import StepUpChallengeModel
from db.repository.step_up_repository import StepUpRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestStepUpRepositoryUnit(unittest.IsolatedAsyncioTestCase):
    """Unit test suite for StepUpRepository."""

    async def test_create_challenge_flushes(self) -> None:
        """Verify create_challenge adds model to session and flushes."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = StepUpRepository(mock_session)

        exp = _utc_now() + timedelta(minutes=15)
        ch = await repo.create_challenge(
            challenge_id="ch_unit_1",
            transaction_id="tx_1",
            risk_classification="HIGH_AMOUNT",
            expires_at=exp,
        )

        self.assertEqual(ch.challenge_id, "ch_unit_1")
        self.assertEqual(ch.status, StepUpChallengeStatus.PENDING.value)
        mock_session.add.assert_called_once_with(ch)
        mock_session.flush.assert_awaited_once()

    async def test_approve_challenge_success(self) -> None:
        """Verify approve_challenge transitions PENDING -> APPROVED and sets metadata."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        exp = _utc_now() + timedelta(minutes=15)
        ch = StepUpChallengeModel(
            challenge_id="ch_unit_2",
            transaction_id="tx_2",
            status=StepUpChallengeStatus.PENDING.value,
            risk_classification="HIGH_AMOUNT",
            expires_at=exp,
        )
        mock_result.scalar_one_or_none.return_value = ch
        mock_session.execute.return_value = mock_result

        repo = StepUpRepository(mock_session)
        approved = await repo.approve_challenge("ch_unit_2", "human_user_42")

        self.assertEqual(approved.status, StepUpChallengeStatus.APPROVED.value)
        self.assertIsNotNone(approved.approved_at)
        self.assertEqual(approved.approver_metadata, "approved_by:human_user_42")

    async def test_approve_expired_challenge_fails_closed(self) -> None:
        """Verify approving an expired challenge transitions status to EXPIRED and raises ValueError."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        past_exp = _utc_now() - timedelta(minutes=5)
        ch = StepUpChallengeModel(
            challenge_id="ch_expired",
            transaction_id="tx_3",
            status=StepUpChallengeStatus.PENDING.value,
            risk_classification="HIGH_AMOUNT",
            expires_at=past_exp,
        )
        mock_result.scalar_one_or_none.return_value = ch
        mock_session.execute.return_value = mock_result

        repo = StepUpRepository(mock_session)
        with self.assertRaises(ValueError) as ctx:
            await repo.approve_challenge("ch_expired", "human_user_42")

        self.assertIn("expired", str(ctx.exception))
        self.assertEqual(ch.status, StepUpChallengeStatus.EXPIRED.value)


if __name__ == "__main__":
    unittest.main()
