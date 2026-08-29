"""
Integration tests for S05.3.5 BudgetRepository against SQLite in-memory database.
"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.domain.types import BudgetState
from db.models.base import Base
from db.repository.budget_repository import BudgetRepository
from db.repository.mandate_repository import MandateRepository
from db.repository.merchant_repository import MerchantRepository
from db.repository.transaction_repository import TransactionRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestBudgetRepositoryIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test suite for BudgetRepository using SQLite in-memory engine."""

    async def asyncSetUp(self) -> None:
        """Set up in-memory SQLite database and repository sessions."""
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self.session = self.session_factory()
        self.merchant_repo = MerchantRepository(self.session)
        self.mandate_repo = MandateRepository(self.session)
        self.tx_repo = TransactionRepository(self.session)
        self.budget_repo = BudgetRepository(self.session)

        # Seed merchant, mandate (daily limit: 10,000 paise = ₹100), and transaction
        await self.merchant_repo.create_merchant("m_bgt_1", "Budget Merchant")
        exp = _utc_now() + timedelta(days=30)
        await self.mandate_repo.create_mandate(
            mandate_id="man_bgt_1",
            buyer_id="buyer_bgt_1",
            merchant_id="m_bgt_1",
            daily_budget_paise=10000,
            expires_at=exp,
        )
        await self.tx_repo.create_transaction(
            transaction_id="tx_bgt_1",
            buyer_id="buyer_bgt_1",
            merchant_id="m_bgt_1",
            mandate_id="man_bgt_1",
            amount_paise=2000,
            cart_hash="cart_bgt_1",
            idempotency_key="idemp_bgt_1",
        )
        await self.session.commit()

    async def asyncTearDown(self) -> None:
        """Close session and dispose engine."""
        await self.session.close()
        await self.engine.dispose()

    async def test_atomic_reservation_success_and_overspend_rejection(self) -> None:
        """Verify reserve_budget_atomically succeeds within limit and rejects overspending."""
        # 1. Reserve 6,000 paise (Available: 10,000 - 6,000 = 4,000)
        res1 = await self.budget_repo.reserve_budget_atomically(
            reservation_id="res_integ_1",
            mandate_id="man_bgt_1",
            transaction_id="tx_bgt_1",
            requested_paise=6000,
        )
        await self.session.commit()
        self.assertEqual(res1.reserved_paise, 6000)

        # Create second transaction for second reservation attempt
        await self.tx_repo.create_transaction(
            transaction_id="tx_bgt_2",
            buyer_id="buyer_bgt_1",
            merchant_id="m_bgt_1",
            mandate_id="man_bgt_1",
            amount_paise=5000,
            cart_hash="cart_bgt_2",
            idempotency_key="idemp_bgt_2",
        )
        await self.session.commit()

        # 2. Attempting to reserve 5,000 paise when only 4,000 paise available must fail closed
        with self.assertRaises(ValueError) as ctx:
            await self.budget_repo.reserve_budget_atomically(
                reservation_id="res_integ_2",
                mandate_id="man_bgt_1",
                transaction_id="tx_bgt_2",
                requested_paise=5000,
            )
        self.assertIn("Budget insufficient", str(ctx.exception))

    async def test_released_reservation_frees_budget(self) -> None:
        """Verify releasing a reservation frees budget for subsequent reservations."""
        # Create initial reservation of 10,000 paise (full limit)
        await self.budget_repo.reserve_budget_atomically(
            reservation_id="res_rel_1",
            mandate_id="man_bgt_1",
            transaction_id="tx_bgt_1",
            requested_paise=10000,
        )
        await self.session.commit()

        # Available budget is now 0
        total_reserved = await self.budget_repo.calculate_reserved_total("man_bgt_1")
        self.assertEqual(total_reserved, 10000)

        # Release reservation
        await self.budget_repo.release_reservation("res_rel_1")
        await self.session.commit()

        # Available budget should be restored to 10,000
        total_after_release = await self.budget_repo.calculate_reserved_total("man_bgt_1")
        self.assertEqual(total_after_release, 0)

        # New reservation of 10,000 paise should now succeed
        await self.tx_repo.create_transaction(
            transaction_id="tx_bgt_3",
            buyer_id="buyer_bgt_1",
            merchant_id="m_bgt_1",
            mandate_id="man_bgt_1",
            amount_paise=10000,
            cart_hash="cart_bgt_3",
            idempotency_key="idemp_bgt_3",
        )
        await self.session.commit()

        res2 = await self.budget_repo.reserve_budget_atomically(
            reservation_id="res_rel_2",
            mandate_id="man_bgt_1",
            transaction_id="tx_bgt_3",
            requested_paise=10000,
        )
        await self.session.commit()
        self.assertEqual(res2.state, BudgetState.RESERVED.value)

    async def test_duplicate_mandate_transaction_reservation_rejection(self) -> None:
        """Verify duplicate (mandate_id, transaction_id) reservation raises IntegrityError."""
        await self.budget_repo.reserve_budget_atomically(
            reservation_id="res_dupl_1",
            mandate_id="man_bgt_1",
            transaction_id="tx_bgt_1",
            requested_paise=3000,
        )
        await self.session.commit()

        # Second attempt for same mandate + transaction must raise IntegrityError
        with self.assertRaises(IntegrityError):
            async with self.session_factory() as session2:
                repo2 = BudgetRepository(session2)
                await repo2.create_reservation(
                    reservation_id="res_dupl_2",
                    mandate_id="man_bgt_1",
                    transaction_id="tx_bgt_1",
                    requested_paise=3000,
                    reserved_paise=3000,
                )
                await session2.commit()

    async def test_concurrency_no_overspend(self) -> None:
        """
        Concurrency-Oriented Test:
        10 workers concurrently attempt to reserve 2,000 paise each against a 10,000 paise limit.
        Invariant: Exactly 5 workers succeed (total 10,000 paise), 5 fail. 0 overspend!
        """
        successes = 0
        failures = 0

        async def worker_attempt(worker_idx: int) -> bool:
            tx_id = f"tx_worker_{worker_idx}"
            res_id = f"res_worker_{worker_idx}"
            async with self.session_factory() as session_worker:
                tx_repo_w = TransactionRepository(session_worker)
                bgt_repo_w = BudgetRepository(session_worker)

                try:
                    await tx_repo_w.create_transaction(
                        transaction_id=tx_id,
                        buyer_id="buyer_bgt_1",
                        merchant_id="m_bgt_1",
                        mandate_id="man_bgt_1",
                        amount_paise=2000,
                        cart_hash=f"cart_{worker_idx}",
                        idempotency_key=f"idemp_worker_{worker_idx}",
                    )
                    await bgt_repo_w.reserve_budget_atomically(
                        reservation_id=res_id,
                        mandate_id="man_bgt_1",
                        transaction_id=tx_id,
                        requested_paise=2000,
                    )
                    await session_worker.commit()
                    return True
                except (ValueError, IntegrityError):
                    await session_worker.rollback()
                    return False

        results = await asyncio.gather(*[worker_attempt(i) for i in range(10)])
        successes = sum(1 for r in results if r is True)
        failures = sum(1 for r in results if r is False)

        self.assertEqual(successes, 5)
        self.assertEqual(failures, 5)

        # Check total reserved in DB is exactly 10,000 paise
        total_reserved = await self.budget_repo.calculate_reserved_total("man_bgt_1")
        self.assertEqual(total_reserved, 10000)


if __name__ == "__main__":
    unittest.main()
