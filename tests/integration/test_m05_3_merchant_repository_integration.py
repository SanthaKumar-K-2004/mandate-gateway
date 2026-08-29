"""
Integration tests for S05.3.2 MerchantRepository against SQLite in-memory database.
"""

from __future__ import annotations

import unittest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models.base import Base
from db.repository.merchant_repository import MerchantRepository


class TestMerchantRepositoryIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test suite for MerchantRepository using SQLite in-memory engine."""

    async def asyncSetUp(self) -> None:
        """Set up in-memory SQLite database and repository session."""
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self.session = self.session_factory()
        self.repo = MerchantRepository(self.session)

    async def asyncTearDown(self) -> None:
        """Close session and dispose engine."""
        await self.session.close()
        await self.engine.dispose()

    async def test_merchant_lifecycle(self) -> None:
        """Verify merchant creation, retrieval by ID, and retrieval by Razorpay account."""
        await self.repo.create_merchant(
            merchant_id="m_integ_101",
            name="Integ Merchant",
            razorpay_account_id="acc_integ_101",
        )
        await self.session.commit()

        fetched_by_id = await self.repo.get_by_id("m_integ_101")
        self.assertIsNotNone(fetched_by_id)
        self.assertEqual(fetched_by_id.name, "Integ Merchant")  # type: ignore[union-attr]

        fetched_by_acc = await self.repo.get_merchant_by_account("acc_integ_101")
        self.assertIsNotNone(fetched_by_acc)
        self.assertEqual(fetched_by_acc.merchant_id, "m_integ_101")  # type: ignore[union-attr]

    async def test_duplicate_razorpay_account_rejection(self) -> None:
        """Verify duplicate razorpay_account_id raises IntegrityError."""
        await self.repo.create_merchant("m_1", "Merchant 1", "acc_duplicate")
        await self.session.commit()

        with self.assertRaises(IntegrityError):
            async with self.session_factory() as session2:
                repo2 = MerchantRepository(session2)
                await repo2.create_merchant("m_2", "Merchant 2", "acc_duplicate")
                await session2.commit()

    async def test_policy_version_uniqueness_and_active_retrieval(self) -> None:
        """Verify policy version uniqueness and active policy retrieval."""
        await self.repo.create_merchant("m_pol_1", "Policy Merchant")
        await self.session.commit()

        await self.repo.create_policy(
            policy_id="pol_1",
            merchant_id="m_pol_1",
            policy_version="v1.0",
            autonomous_limit_paise=100000,
            step_up_threshold_paise=200000,
            allowed_categories=["saas"],
        )
        await self.session.commit()

        # Duplicate version for same merchant must raise IntegrityError
        with self.assertRaises(IntegrityError):
            async with self.session_factory() as session2:
                repo2 = MerchantRepository(session2)
                await repo2.create_policy(
                    policy_id="pol_2",
                    merchant_id="m_pol_1",
                    policy_version="v1.0",
                    autonomous_limit_paise=100000,
                    step_up_threshold_paise=200000,
                )
                await session2.commit()

        # Retrieve active policy
        active_pol = await self.repo.get_active_policy("m_pol_1")
        self.assertIsNotNone(active_pol)
        self.assertEqual(active_pol.id, "pol_1")  # type: ignore[union-attr]

    async def test_product_lifecycle_and_negative_price_rejection(self) -> None:
        """Verify product creation, listing, and negative price check constraint rejection."""
        await self.repo.create_merchant("m_prod_1", "Product Merchant")
        await self.session.commit()

        await self.repo.create_product(
            product_id="prod_1",
            merchant_id="m_prod_1",
            name="Pro Subscription",
            price_paise=50000,
            category="saas",
        )
        await self.session.commit()

        products = await self.repo.list_products("m_prod_1")
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, "Pro Subscription")

        # Negative price must raise IntegrityError
        with self.assertRaises(IntegrityError):
            async with self.session_factory() as session2:
                repo2 = MerchantRepository(session2)
                await repo2.create_product(
                    product_id="prod_invalid",
                    merchant_id="m_prod_1",
                    name="Invalid Price Product",
                    price_paise=-500,
                    category="saas",
                )
                await session2.commit()

    async def test_transaction_rollback_safety(self) -> None:
        """Verify transaction rollback leaves session clean without committing partial state."""
        await self.repo.create_merchant("m_roll_1", "Rollback Merchant")
        await self.session.commit()

        try:
            await self.repo.create_product(
                product_id="prod_roll_invalid",
                merchant_id="m_roll_1",
                name="Bad Product",
                price_paise=-100,  # Fails check constraint
                category="saas",
            )
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()

        # Session should be clean and rollback merchant still exists intact
        merchant = await self.repo.get_by_id("m_roll_1")
        self.assertIsNotNone(merchant)
        products = await self.repo.list_products("m_roll_1")
        self.assertEqual(len(products), 0)


if __name__ == "__main__":
    unittest.main()
