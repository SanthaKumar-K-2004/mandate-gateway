"""
Unit tests for S05.3.7 ReceiptRepository.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.receipt import ActionReceiptModel
from db.repository.base import BaseRepository
from db.repository.receipt_repository import ReceiptRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestReceiptRepositoryUnit(unittest.IsolatedAsyncioTestCase):
    """Unit test suite for ReceiptRepository."""

    async def test_inherits_base_repository(self) -> None:
        """Verify ReceiptRepository inherits from BaseRepository."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = ReceiptRepository(mock_session)
        self.assertIsInstance(repo, BaseRepository)
        self.assertEqual(repo.model_cls, ActionReceiptModel)

    async def test_create_receipt_flushes(self) -> None:
        """Verify create_receipt adds model to session and flushes without commit."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = ReceiptRepository(mock_session)

        rcpt = await repo.create_receipt(
            receipt_id="rcpt_unit_1",
            transaction_id="tx_unit_1",
            audit_event_id="evt_unit_1",
            canonical_payload_hash="payload_hash_123",
            signature_hex="sig_hex_123",
            public_key_hex="pubkey_hex_123",
        )

        self.assertEqual(rcpt.receipt_id, "rcpt_unit_1")
        self.assertEqual(rcpt.canonical_payload_hash, "payload_hash_123")
        mock_session.add.assert_called_once_with(rcpt)
        mock_session.flush.assert_awaited_once()

    async def test_empty_fields_raise_value_error(self) -> None:
        """Verify empty inputs raise ValueError."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = ReceiptRepository(mock_session)

        with self.assertRaises(ValueError):
            await repo.create_receipt("", "tx_1", "evt_1", "hash", "sig", "pub")

        with self.assertRaises(ValueError):
            await repo.create_receipt("rcpt_1", "", "evt_1", "hash", "sig", "pub")


if __name__ == "__main__":
    unittest.main()
