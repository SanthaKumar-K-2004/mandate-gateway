"""
Unit tests for S05.3.6.3 NonceRepository.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.domain.types import NonceState
from db.models.replay import NonceRecordModel
from db.repository.base import BaseRepository
from db.repository.nonce_repository import NonceRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestNonceRepositoryUnit(unittest.IsolatedAsyncioTestCase):
    """Unit test suite for NonceRepository."""

    async def test_inherits_base_repository(self) -> None:
        """Verify NonceRepository inherits from BaseRepository."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = NonceRepository(mock_session)
        self.assertIsInstance(repo, BaseRepository)
        self.assertEqual(repo.model_cls, NonceRecordModel)

    async def test_create_nonce_flushes(self) -> None:
        """Verify create_nonce adds model to session and flushes without commit."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = NonceRepository(mock_session)

        n_val = "n_unit_1"
        tx_id = "tx_unit_1"
        man_id = "man_unit_1"
        rec = await repo.create_nonce(n_val, tx_id, man_id)

        self.assertEqual(rec.nonce, n_val)
        self.assertEqual(rec.status, NonceState.ISSUED.value)
        self.assertIsNone(rec.consumed_at)
        mock_session.add.assert_called_once_with(rec)
        mock_session.flush.assert_awaited_once()

    async def test_consume_nonce_success(self) -> None:
        """Verify consume_nonce transitions ISSUED -> CONSUMED."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        rec = NonceRecordModel(
            nonce="n_unit_2",
            transaction_id="tx_unit_2",
            mandate_id="man_unit_2",
            status=NonceState.ISSUED.value,
            created_at=_utc_now(),
            consumed_at=None,
        )
        mock_result.scalar_one_or_none.return_value = rec
        mock_session.execute.return_value = mock_result

        repo = NonceRepository(mock_session)
        consumed = await repo.consume_nonce("n_unit_2", "tx_unit_2", "man_unit_2")

        self.assertEqual(consumed.status, NonceState.CONSUMED.value)
        self.assertIsNotNone(consumed.consumed_at)
        mock_session.flush.assert_awaited()

    async def test_consume_expired_nonce_fails_closed(self) -> None:
        """Verify consuming an expired nonce raises ValueError."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        past_time = _utc_now() - timedelta(seconds=600)
        rec = NonceRecordModel(
            nonce="n_unit_exp",
            transaction_id="tx_unit_3",
            mandate_id="man_unit_3",
            status=NonceState.ISSUED.value,
            created_at=past_time,
            consumed_at=None,
        )
        mock_result.scalar_one_or_none.return_value = rec
        mock_session.execute.return_value = mock_result

        repo = NonceRepository(mock_session)
        with self.assertRaises(ValueError) as ctx:
            await repo.consume_nonce("n_unit_exp", "tx_unit_3", "man_unit_3", ttl_seconds=300)

        self.assertIn("expired", str(ctx.exception))

    async def test_context_mismatch_fails_closed(self) -> None:
        """Verify consuming nonce with mismatched transaction or mandate ID raises ValueError."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        rec = NonceRecordModel(
            nonce="n_unit_ctx",
            transaction_id="tx_orig",
            mandate_id="man_orig",
            status=NonceState.ISSUED.value,
            created_at=_utc_now(),
            consumed_at=None,
        )
        mock_result.scalar_one_or_none.return_value = rec
        mock_session.execute.return_value = mock_result

        repo = NonceRepository(mock_session)
        with self.assertRaises(ValueError) as ctx:
            await repo.consume_nonce("n_unit_ctx", "tx_attacker", "man_orig")

        self.assertIn("Nonce context mismatch", str(ctx.exception))

    async def test_double_consumption_fails_closed(self) -> None:
        """Verify consuming an already CONSUMED nonce raises ValueError."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        rec = NonceRecordModel(
            nonce="n_unit_consumed",
            transaction_id="tx_unit_4",
            mandate_id="man_unit_4",
            status=NonceState.CONSUMED.value,
            created_at=_utc_now(),
            consumed_at=_utc_now(),
        )
        mock_result.scalar_one_or_none.return_value = rec
        mock_session.execute.return_value = mock_result

        repo = NonceRepository(mock_session)
        with self.assertRaises(ValueError) as ctx:
            await repo.consume_nonce("n_unit_consumed", "tx_unit_4", "man_unit_4")

        self.assertIn("already been consumed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
