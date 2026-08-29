"""
Unit tests for S05.3.1 BaseRepository foundation.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.merchant import MerchantModel
from db.repository.base import BaseRepository


class TestBaseRepositoryUnit(unittest.IsolatedAsyncioTestCase):
    """Unit test suite for BaseRepository."""

    def test_instantiation_requires_session(self) -> None:
        """Verify instantiation fails if session is None."""
        with self.assertRaises(ValueError) as ctx:
            BaseRepository(MerchantModel, None)  # type: ignore[arg-type]
        self.assertIn("AsyncSession must be explicitly provided", str(ctx.exception))

    def test_properties_exposure(self) -> None:
        """Verify session and model_cls properties return correct references."""
        mock_session = MagicMock(spec=AsyncSession)
        repo = BaseRepository(MerchantModel, mock_session)
        self.assertIs(repo.session, mock_session)
        self.assertIs(repo.model_cls, MerchantModel)

    async def test_get_by_id_calls_session_get(self) -> None:
        """Verify get_by_id delegates to AsyncSession.get with model_cls and entity_id."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_merchant = MerchantModel(merchant_id="m_100", name="Test Merchant")
        mock_session.get.return_value = mock_merchant

        repo = BaseRepository(MerchantModel, mock_session)
        result = await repo.get_by_id("m_100")

        mock_session.get.assert_awaited_once_with(MerchantModel, "m_100")
        self.assertIs(result, mock_merchant)

    async def test_get_by_id_returns_none_when_not_found(self) -> None:
        """Verify get_by_id returns None when session.get returns None."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get.return_value = None

        repo = BaseRepository(MerchantModel, mock_session)
        result = await repo.get_by_id("m_nonexistent")

        mock_session.get.assert_awaited_once_with(MerchantModel, "m_nonexistent")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
