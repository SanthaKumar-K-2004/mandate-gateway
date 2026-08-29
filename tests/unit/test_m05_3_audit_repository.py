"""
Unit tests for S05.3.7 AuditRepository.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.domain.audit import GENESIS_HASH
from apps.api.domain.types import AuditEventType
from db.models.audit import AuditEventModel
from db.repository.audit_repository import AuditRepository
from db.repository.base import BaseRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestAuditRepositoryUnit(unittest.IsolatedAsyncioTestCase):
    """Unit test suite for AuditRepository."""

    async def test_inherits_base_repository(self) -> None:
        """Verify AuditRepository inherits from BaseRepository."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = AuditRepository(mock_session)
        self.assertIsInstance(repo, BaseRepository)
        self.assertEqual(repo.model_cls, AuditEventModel)

    async def test_append_event_first_event_uses_genesis_hash(self) -> None:
        """Verify first appended event uses GENESIS_HASH as previous_hash and sequence_number=1."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        evt = await repo.append_event(
            event_type=AuditEventType.MANDATE_CREATED,
            mandate_id="man_101",
            payload={"action": "create_mandate"},
        )

        self.assertEqual(evt.sequence_number, 1)
        self.assertEqual(evt.previous_hash, GENESIS_HASH)
        self.assertIsNotNone(evt.event_hash)
        mock_session.add.assert_called_once_with(evt)
        mock_session.flush.assert_awaited_once()

    async def test_append_event_subsequent_links_to_previous_hash(self) -> None:
        """Verify second event links to first event_hash and increments sequence."""
        mock_session = AsyncMock(spec=AsyncSession)

        evt1 = AuditEventModel(
            event_id="evt_1",
            sequence_number=1,
            event_type=AuditEventType.MANDATE_CREATED.value,
            previous_hash=GENESIS_HASH,
            event_hash="hash_one_123",
            payload_json="{}",
            timestamp=_utc_now(),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = evt1
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        evt2 = await repo.append_event(
            event_type=AuditEventType.PAYMENT_SUCCESS,
            transaction_id="tx_202",
        )

        self.assertEqual(evt2.sequence_number, 2)
        self.assertEqual(evt2.previous_hash, "hash_one_123")


if __name__ == "__main__":
    unittest.main()
