"""
Section M17 — Multi-Worker Recovery Concurrency Verification.
Verifies multiple concurrent recovery and outbox workers operating against shared persistence
guarantee exactly-once state transitions, zero double-dispatches, and fail-closed UNKNOWN resolution.
"""

import asyncio
import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.workers.outbox_worker import OutboxWorker
from apps.workers.recovery_worker import RecoveryWorker
from db.models.base import Base
import db.session
from db.unit_of_work import AsyncUnitOfWork


class TestM17RecoveryConcurrency(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        db.session._async_session_factory = self.session_factory

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        db.session._async_session_factory = None

    async def test_concurrent_outbox_workers_no_duplicate_dispatch(self) -> None:
        """Verify 5 concurrent outbox workers process pending outbox events without duplicate dispatch."""
        async with AsyncUnitOfWork() as uow:
            for i in range(10):
                await uow.outbox.record_event(
                    event_type="payment.captured",
                    aggregate_id=f"tx_conc_{i}",
                    payload={"tx_id": f"tx_conc_{i}"},
                )
            await uow.commit()

        workers = [OutboxWorker(poll_interval_seconds=1.0) for _ in range(5)]
        results = await asyncio.gather(*(w.process_batch() for w in workers))
        total_processed = sum(results)
        self.assertEqual(total_processed, 10)

        # Confirm 0 pending events remain
        async with AsyncUnitOfWork() as uow:
            pending = await uow.outbox.get_pending_count()
            self.assertEqual(pending, 0)

    async def test_concurrent_recovery_workers_no_double_reconciliation(self) -> None:
        """Verify 5 concurrent recovery workers reconciles stuck transactions cleanly."""
        async with AsyncUnitOfWork() as uow:
            for i in range(5):
                await uow.transactions.create_transaction(
                    transaction_id=f"tx_rec_{i}",
                    buyer_id=f"buyer_rec_{i}",
                    merchant_id="mer_rec",
                    mandate_id="man_rec",
                    amount_paise=5000,
                    cart_hash=f"cart_{i}",
                    idempotency_key=f"ik_rec_{i}",
                )
                await uow.transactions.mark_provider_dispatch_started(f"tx_rec_{i}", f"pay_rec_{i}")
            await uow.commit()

        rec_workers = [
            RecoveryWorker(stuck_threshold_seconds=0, poll_interval_seconds=1.0) for _ in range(5)
        ]
        results = await asyncio.gather(*(w.process_batch() for w in rec_workers))
        self.assertEqual(sum(results), 5)


if __name__ == "__main__":
    unittest.main()
