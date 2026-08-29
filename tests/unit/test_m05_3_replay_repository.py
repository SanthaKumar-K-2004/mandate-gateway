"""
Unit tests for S05.3.6.2 ReplayRepository.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.replay import ReplayRecordModel
from db.repository.base import BaseRepository
from db.repository.replay_repository import ReplayRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestReplayRepositoryUnit(unittest.IsolatedAsyncioTestCase):
    """Unit test suite for ReplayRepository."""

    async def test_inherits_base_repository(self) -> None:
        """Verify ReplayRepository inherits from BaseRepository."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = ReplayRepository(mock_session)
        self.assertIsInstance(repo, BaseRepository)
        self.assertEqual(repo.model_cls, ReplayRecordModel)

    async def test_record_replay_fingerprint_flushes(self) -> None:
        """Verify record_replay_fingerprint adds model and flushes without commit."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = ReplayRepository(mock_session)

        fp = "fp_unit_1"
        tx_id = "tx_unit_1"
        rec = await repo.record_replay_fingerprint(fp, tx_id)

        self.assertEqual(rec.fingerprint, fp)
        self.assertEqual(rec.transaction_id, tx_id)
        mock_session.add.assert_called_once_with(rec)
        mock_session.flush.assert_awaited_once()

    async def test_check_and_record_active_replay_detected(self) -> None:
        """Verify active replay fingerprint detection returning (True, record)."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        rec = ReplayRecordModel(
            fingerprint="fp_unit_active",
            transaction_id="tx_unit_2",
            created_at=_utc_now(),
        )
        mock_result.scalar_one_or_none.return_value = rec
        mock_session.execute.return_value = mock_result

        repo = ReplayRepository(mock_session)
        is_replayed, record = await repo.check_and_record_replay(
            fingerprint="fp_unit_active",
            transaction_id="tx_unit_2",
            ttl_seconds=86400,
        )

        self.assertTrue(is_replayed)
        self.assertIs(record, rec)

    async def test_check_and_record_expired_fingerprint_allowed(self) -> None:
        """Verify expired replay fingerprint allows new record registration."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        past_time = _utc_now() - timedelta(seconds=90000)
        old_rec = ReplayRecordModel(
            fingerprint="fp_unit_exp",
            transaction_id="tx_unit_3",
            created_at=past_time,
        )
        mock_result.scalar_one_or_none.return_value = old_rec
        mock_session.execute.return_value = mock_result

        repo = ReplayRepository(mock_session)
        now_time = _utc_now()

        is_replayed, new_rec = await repo.check_and_record_replay(
            fingerprint="fp_unit_exp",
            transaction_id="tx_unit_3",
            ttl_seconds=86400,
            at=now_time,
        )

        self.assertFalse(is_replayed)
        self.assertIsNotNone(new_rec)
        mock_session.flush.assert_awaited()

    async def test_conflicting_context_reuse_fails_closed(self) -> None:
        """Verify attempting to reuse fingerprint with conflicting transaction_id raises ValueError."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        rec = ReplayRecordModel(
            fingerprint="fp_conflict",
            transaction_id="tx_orig",
            created_at=_utc_now(),
        )
        mock_result.scalar_one_or_none.return_value = rec
        mock_session.execute.return_value = mock_result

        repo = ReplayRepository(mock_session)
        with self.assertRaises(ValueError) as ctx:
            await repo.check_and_record_replay(
                fingerprint="fp_conflict",
                transaction_id="tx_attacker",
            )

        self.assertIn("Conflicting context reuse detected", str(ctx.exception))

    async def test_invalid_input_fails_closed(self) -> None:
        """Verify empty fingerprint or transaction ID raises ValueError."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = ReplayRepository(mock_session)

        with self.assertRaises(ValueError):
            await repo.record_replay_fingerprint("", "tx_1")

        with self.assertRaises(ValueError):
            await repo.record_replay_fingerprint("fp_1", "")


if __name__ == "__main__":
    unittest.main()
