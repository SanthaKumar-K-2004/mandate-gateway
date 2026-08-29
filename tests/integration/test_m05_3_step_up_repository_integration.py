"""
Integration tests for S05.3.6.1 StepUpRepository against SQLite in-memory database.
"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.domain.step_up import StepUpChallengeStatus
from db.models.base import Base
from db.repository.merchant_repository import MerchantRepository
from db.repository.step_up_repository import StepUpRepository
from db.repository.transaction_repository import TransactionRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestStepUpRepositoryIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test suite for StepUpRepository using SQLite in-memory engine."""

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
        self.tx_repo = TransactionRepository(self.session)
        self.step_up_repo = StepUpRepository(self.session)

        # Seed merchant & transaction
        await self.merchant_repo.create_merchant("m_su_1", "StepUp Merchant")
        await self.tx_repo.create_transaction(
            transaction_id="tx_su_1",
            buyer_id="buyer_su_1",
            merchant_id="m_su_1",
            mandate_id="man_su_1",
            amount_paise=500000,
            cart_hash="cart_su_1",
            idempotency_key="idemp_su_1",
        )
        await self.session.commit()

    async def asyncTearDown(self) -> None:
        """Close session and dispose engine."""
        await self.session.close()
        await self.engine.dispose()

    async def test_challenge_lifecycle_and_single_approval(self) -> None:
        """Verify challenge creation, retrieval, approval, and double-approval rejection."""
        exp = _utc_now() + timedelta(minutes=15)
        await self.step_up_repo.create_challenge(
            challenge_id="ch_integ_1",
            transaction_id="tx_su_1",
            risk_classification="HIGH_AMOUNT",
            expires_at=exp,
        )
        await self.session.commit()

        ch = await self.step_up_repo.get_challenge("ch_integ_1")
        self.assertIsNotNone(ch)
        self.assertEqual(ch.status, StepUpChallengeStatus.PENDING.value)  # type: ignore[union-attr]

        # Approve challenge
        approved = await self.step_up_repo.approve_challenge("ch_integ_1", "human_approver_1")
        await self.session.commit()
        self.assertEqual(approved.status, StepUpChallengeStatus.APPROVED.value)

        # Second approval attempt must fail closed (Double Approval Security Requirement)
        with self.assertRaises(ValueError):
            async with self.session_factory() as session2:
                repo2 = StepUpRepository(session2)
                await repo2.approve_challenge("ch_integ_1", "human_approver_2")

    async def test_expired_challenge_approval_rejection(self) -> None:
        """Verify approving an expired challenge fails closed and mutates state to EXPIRED."""
        past_exp = _utc_now() - timedelta(minutes=1)
        await self.step_up_repo.create_challenge(
            challenge_id="ch_integ_exp",
            transaction_id="tx_su_1",
            risk_classification="HIGH_AMOUNT",
            expires_at=past_exp,
        )
        await self.session.commit()

        with self.assertRaises(ValueError) as ctx:
            await self.step_up_repo.approve_challenge("ch_integ_exp", "human_approver_1")

        self.assertIn("expired", str(ctx.exception))

        ch_after = await self.step_up_repo.get_challenge("ch_integ_exp")
        self.assertIsNotNone(ch_after)
        self.assertEqual(ch_after.status, StepUpChallengeStatus.EXPIRED.value)  # type: ignore[union-attr]

    async def test_concurrent_exact_once_approval(self) -> None:
        """
        Critical Exact-Once Approval Invariant Test:
        10 workers concurrently attempt to approve the same step-up challenge.
        Invariant: Exactly 1 worker succeeds, 9 fail with ValueError. Double approvals = 0!
        """
        exp = _utc_now() + timedelta(minutes=15)
        await self.step_up_repo.create_challenge(
            challenge_id="ch_race_1",
            transaction_id="tx_su_1",
            risk_classification="HIGH_AMOUNT",
            expires_at=exp,
        )
        await self.session.commit()

        async def worker_approve(worker_idx: int) -> bool:
            async with self.session_factory() as session_worker:
                repo_w = StepUpRepository(session_worker)
                try:
                    await repo_w.approve_challenge("ch_race_1", f"approver_{worker_idx}")
                    await session_worker.commit()
                    return True
                except ValueError:
                    await session_worker.rollback()
                    return False

        results = await asyncio.gather(*[worker_approve(i) for i in range(10)])
        successes = sum(1 for r in results if r is True)
        failures = sum(1 for r in results if r is False)

        self.assertEqual(successes, 1)
        self.assertEqual(failures, 9)

        ch_final = await self.step_up_repo.get_challenge("ch_race_1")
        self.assertIsNotNone(ch_final)
        self.assertEqual(ch_final.status, StepUpChallengeStatus.APPROVED.value)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
