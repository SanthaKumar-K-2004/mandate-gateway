"""
Integration tests for S05.3.3 MandateRepository against SQLite in-memory database.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.domain.mandate_lifecycle import MandateStateTransitionError
from apps.api.domain.types import MandateStatus
from db.models.base import Base
from db.repository.mandate_repository import MandateRepository
from db.repository.merchant_repository import MerchantRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestMandateRepositoryIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test suite for MandateRepository using SQLite in-memory engine."""

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
        self.merchant_repo = MerchantRepository(self.session)
        self.mandate_repo = MandateRepository(self.session)

    async def asyncTearDown(self) -> None:
        """Close session and dispose engine."""
        await self.session.close()
        await self.engine.dispose()

    async def test_mandate_lifecycle_and_buyer_isolation(self) -> None:
        """Verify mandate creation, buyer isolation, and active mandate querying."""
        await self.merchant_repo.create_merchant("m_man_1", "Mandate Merchant")
        await self.session.commit()

        exp = _utc_now() + timedelta(days=30)
        await self.mandate_repo.create_mandate(
            mandate_id="man_integ_1",
            buyer_id="buyer_alice",
            merchant_id="m_man_1",
            daily_budget_paise=500000,
            expires_at=exp,
        )
        await self.session.commit()

        # Buyer Alice should find mandate
        alice_mandate = await self.mandate_repo.get_mandate_for_buyer("man_integ_1", "buyer_alice")
        self.assertIsNotNone(alice_mandate)
        self.assertEqual(alice_mandate.daily_budget_paise, 500000)  # type: ignore[union-attr]

        # Buyer Bob attempting to access Alice's mandate must get None (Buyer Isolation)
        bob_mandate = await self.mandate_repo.get_mandate_for_buyer("man_integ_1", "buyer_bob")
        self.assertIsNone(bob_mandate)

    async def test_get_active_mandates_excludes_expired_or_revoked(self) -> None:
        """Verify active mandates query filters out expired or revoked mandates."""
        await self.merchant_repo.create_merchant("m_man_2", "Merchant 2")
        await self.session.commit()

        future = _utc_now() + timedelta(days=10)
        past = _utc_now() - timedelta(days=1)

        # 1. Active & unexpired
        await self.mandate_repo.create_mandate(
            mandate_id="m_active",
            buyer_id="buyer_carol",
            merchant_id="m_man_2",
            daily_budget_paise=100000,
            expires_at=future,
            status=MandateStatus.ACTIVE,
        )
        # 2. Expired timestamp
        await self.mandate_repo.create_mandate(
            mandate_id="m_expired_ts",
            buyer_id="buyer_carol",
            merchant_id="m_man_2",
            daily_budget_paise=100000,
            expires_at=past,
            status=MandateStatus.ACTIVE,
        )
        # 3. Revoked status
        await self.mandate_repo.create_mandate(
            mandate_id="m_revoked",
            buyer_id="buyer_carol",
            merchant_id="m_man_2",
            daily_budget_paise=100000,
            expires_at=future,
            status=MandateStatus.REVOKED,
        )
        await self.session.commit()

        active_mandates = await self.mandate_repo.get_active_mandates_for_buyer("buyer_carol")
        self.assertEqual(len(active_mandates), 1)
        self.assertEqual(active_mandates[0].mandate_id, "m_active")

    async def test_status_transition_and_terminal_state_lock(self) -> None:
        """Verify legal status transition ACTIVE -> REVOKED and terminal state locking."""
        exp = _utc_now() + timedelta(days=30)
        await self.mandate_repo.create_mandate(
            mandate_id="m_trans",
            buyer_id="buyer_dave",
            daily_budget_paise=200000,
            expires_at=exp,
        )
        await self.session.commit()

        # Transition ACTIVE -> REVOKED
        revoked = await self.mandate_repo.revoke_mandate("m_trans")
        self.assertEqual(revoked.status, MandateStatus.REVOKED.value)
        await self.session.commit()

        # Attempting illegal transition REVOKED -> ACTIVE must fail closed
        with self.assertRaises(MandateStateTransitionError):
            async with self.session_factory() as session2:
                repo2 = MandateRepository(session2)
                await repo2.transition_mandate_status("m_trans", MandateStatus.ACTIVE)

    async def test_negative_daily_budget_check_constraint(self) -> None:
        """Verify negative daily_budget_paise raises IntegrityError."""
        exp = _utc_now() + timedelta(days=30)
        with self.assertRaises(IntegrityError):
            await self.mandate_repo.create_mandate(
                mandate_id="m_neg",
                buyer_id="buyer_eve",
                daily_budget_paise=-1000,
                expires_at=exp,
            )
            await self.session.commit()

    async def test_row_locking_query_construction(self) -> None:
        """Verify lock_mandate_for_update retrieves entity successfully."""
        exp = _utc_now() + timedelta(days=30)
        await self.mandate_repo.create_mandate(
            mandate_id="m_lock",
            buyer_id="buyer_frank",
            daily_budget_paise=300000,
            expires_at=exp,
        )
        await self.session.commit()

        locked = await self.mandate_repo.lock_mandate_for_update("m_lock")
        self.assertIsNotNone(locked)
        self.assertEqual(locked.mandate_id, "m_lock")  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
