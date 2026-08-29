"""
Unit tests for S05.3.2 MerchantRepository.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.merchant import MerchantModel
from db.repository.merchant_repository import MerchantRepository


class TestMerchantRepositoryUnit(unittest.IsolatedAsyncioTestCase):
    """Unit test suite for MerchantRepository."""

    async def test_create_merchant_flushes(self) -> None:
        """Verify create_merchant adds entity to session and flushes."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = MerchantRepository(mock_session)

        merchant = await repo.create_merchant(
            merchant_id="m_unit_1",
            name="Unit Merchant",
            razorpay_account_id="acc_unit_1",
        )

        self.assertEqual(merchant.merchant_id, "m_unit_1")
        self.assertEqual(merchant.name, "Unit Merchant")
        self.assertEqual(merchant.razorpay_account_id, "acc_unit_1")
        mock_session.add.assert_called_once_with(merchant)
        mock_session.flush.assert_awaited_once()

    async def test_get_merchant_by_account(self) -> None:
        """Verify get_merchant_by_account executes select query."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_merchant = MerchantModel(merchant_id="m_unit_2", razorpay_account_id="acc_unit_2")
        mock_result.scalar_one_or_none.return_value = mock_merchant
        mock_session.execute.return_value = mock_result

        repo = MerchantRepository(mock_session)
        result = await repo.get_merchant_by_account("acc_unit_2")

        mock_session.execute.assert_awaited_once()
        self.assertIs(result, mock_merchant)

    async def test_create_policy_serialization(self) -> None:
        """Verify create_policy serializes list fields into JSON strings."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = MerchantRepository(mock_session)

        policy = await repo.create_policy(
            policy_id="pol_unit_1",
            merchant_id="m_unit_1",
            policy_version="v1.0",
            autonomous_limit_paise=50000,
            step_up_threshold_paise=100000,
            allowed_categories=["saas", "cloud"],
        )

        self.assertEqual(policy.id, "pol_unit_1")
        self.assertEqual(policy.allowed_categories_json, '["saas", "cloud"]')
        mock_session.add.assert_called_once_with(policy)
        mock_session.flush.assert_awaited_once()

    async def test_create_product(self) -> None:
        """Verify create_product instantiates and flushes product."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = MerchantRepository(mock_session)

        product = await repo.create_product(
            product_id="prod_unit_1",
            merchant_id="m_unit_1",
            name="API Subscription",
            price_paise=299900,
            category="saas",
        )

        self.assertEqual(product.product_id, "prod_unit_1")
        self.assertEqual(product.price_paise, 299900)
        mock_session.add.assert_called_once_with(product)
        mock_session.flush.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
