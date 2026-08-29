"""
Integration tests for S05.4.2 AsyncUnitOfWork against SQLite in-memory database.
"""

from __future__ import annotations

import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.domain.types import AuditEventType
from db.models.base import Base
from db.unit_of_work import AsyncUnitOfWork


class TestAsyncUnitOfWorkIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test suite for AsyncUnitOfWork using SQLite in-memory engine."""

    async def asyncSetUp(self) -> None:
        """Set up in-memory SQLite database and session factory."""
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def asyncTearDown(self) -> None:
        """Dispose database engine."""
        await self.engine.dispose()

    async def test_multi_repository_atomic_commit(self) -> None:
        """Verify atomic commit across multiple repositories in single UoW."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            # 1. Merchant
            m = await uow.merchants.create_merchant("m_uow_1", "UoW Merchant")
            from datetime import datetime, timedelta, timezone

            exp = datetime.now(tz=timezone.utc) + timedelta(days=1)
            # 2. Mandate
            await uow.mandates.create_mandate(
                mandate_id="man_uow_1",
                buyer_id="buyer_uow_1",
                daily_budget_paise=200000,
                expires_at=exp,
                merchant_id=m.merchant_id,
            )
            # 3. Transaction
            await uow.transactions.create_transaction(
                transaction_id="tx_uow_1",
                buyer_id="buyer_uow_1",
                merchant_id=m.merchant_id,
                mandate_id="man_uow_1",
                amount_paise=25000,
                cart_hash="a" * 64,
                idempotency_key="idemp_uow_1",
            )
            # 4. Audit
            await uow.audit.append_event(
                event_type=AuditEventType.MANDATE_CREATED,
                transaction_id="tx_uow_1",
                mandate_id="man_uow_1",
                merchant_id=m.merchant_id,
                payload={"test": "uow_commit"},
            )

            # Explicit Commit
            await uow.commit()

        # Verify persistence in a fresh separate UoW session
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow2:
            db_m = await uow2.merchants.get_merchant_by_account("m_uow_1")
            db_man = await uow2.mandates.get_mandate("man_uow_1")
            db_tx = await uow2.transactions.get_transaction("tx_uow_1")
            db_events = await uow2.audit.get_events_for_transaction("tx_uow_1")

            self.assertIsNotNone(db_m)
            self.assertIsNotNone(db_man)
            self.assertIsNotNone(db_tx)
            self.assertEqual(len(db_events), 1)

    async def test_multi_repository_rollback_leaves_zero_partial_state(self) -> None:
        """Verify exception during multi-repository operation rolls back all uncommitted state."""
        from datetime import datetime, timedelta, timezone

        exp = datetime.now(tz=timezone.utc) + timedelta(days=1)
        with self.assertRaises(ValueError):
            async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
                # 1. Merchant
                await uow.merchants.create_merchant("m_uow_fail", "Failed Merchant")
                # 2. Mandate
                await uow.mandates.create_mandate(
                    mandate_id="man_uow_fail",
                    buyer_id="buyer_uow_fail",
                    daily_budget_paise=200000,
                    expires_at=exp,
                    merchant_id="m_uow_fail",
                )
                # Raise error before commit
                raise ValueError("Simulated Operation Failure")

        # Verify NOTHING persisted in fresh session
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow2:
            db_m = await uow2.merchants.get_merchant_by_account("m_uow_fail")
            db_man = await uow2.mandates.get_mandate("man_uow_fail")

            self.assertIsNone(db_m)
            self.assertIsNone(db_man)

    async def test_exit_without_commit_does_not_persist(self) -> None:
        """Verify exiting UoW block without calling commit() discards uncommitted flushes."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.merchants.create_merchant("m_uow_uncommitted", "Uncommitted Merchant")
            # Intentionally omit await uow.commit()

        # Verify entity does not exist in DB
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow2:
            db_m = await uow2.merchants.get_merchant_by_account("m_uow_uncommitted")
            self.assertIsNone(db_m)

    async def test_same_session_repository_sharing_and_uow_isolation(self) -> None:
        """Verify repositories within one UoW share session, while separate UoWs get distinct sessions."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow1:
            session_1 = uow1.merchants.session
            self.assertIs(uow1.mandates.session, session_1)
            self.assertIs(uow1.transactions.session, session_1)

            async with AsyncUnitOfWork(session_factory=self.session_factory) as uow2:
                session_2 = uow2.merchants.session
                self.assertIsNot(session_1, session_2)


if __name__ == "__main__":
    unittest.main()
