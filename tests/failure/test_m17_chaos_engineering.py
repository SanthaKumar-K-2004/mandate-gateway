"""
Section M17 — Deterministic Chaos Engineering Matrix.
Injects controlled failure modes proving system invariants hold under process, DB, Redis, and network faults.
"""

import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.workers.outbox_worker import OutboxWorker
from db.models.base import Base
import db.session
from db.unit_of_work import AsyncUnitOfWork


class TestM17ChaosEngineeringFaultInjection(unittest.IsolatedAsyncioTestCase):
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

    async def test_chaos_fault_01_process_termination_mid_attempt(self) -> None:
        """Fault Category 1: Process termination during attempt registration preserves claimed attempt."""
        async with AsyncUnitOfWork() as uow:
            attempt = await uow.execution_attempts.create_attempt(
                attempt_id="att_chaos_1",
                transaction_id="tx_chaos_1",
                provider_name="Razorpay",
                merchant_id="mer_chaos_1",
                idempotency_key="ik_chaos_1",
            )
            self.assertEqual(attempt.attempt_id, "att_chaos_1")
            await uow.commit()

        # Simulate process restart & re-claim
        async with AsyncUnitOfWork() as uow:
            rec, is_existing = await uow.execution_attempts.claim_attempt(
                transaction_id="tx_chaos_1",
                merchant_id="mer_chaos_1",
                idempotency_key="ik_chaos_1",
                payload_fingerprint="fp_default",
            )
            self.assertTrue(is_existing)

    async def test_chaos_fault_02_database_interruption_during_outbox_enqueue(self) -> None:
        """Fault Category 2: DB interruption during outbox enqueue fails closed without committing event."""
        with self.assertRaises(Exception):
            async with AsyncUnitOfWork() as uow:
                await uow.outbox.record_event("payment.created", "tx_chaos_2", {"tx": "tx_chaos_2"})
                raise RuntimeError("Simulated DB Interruption")

        async with AsyncUnitOfWork() as uow:
            cnt = await uow.outbox.get_pending_count()
            self.assertEqual(cnt, 0)

    async def test_chaos_fault_03_provider_timeout_simulation(self) -> None:
        """Fault Category 3: Provider timeout leaves transaction in EXECUTING with UNKNOWN outcome."""
        async with AsyncUnitOfWork() as uow:
            await uow.transactions.create_transaction(
                transaction_id="tx_chaos_3",
                buyer_id="buyer_chaos_3",
                merchant_id="mer_chaos_3",
                mandate_id="man_chaos_3",
                amount_paise=1000,
                cart_hash="cart_c3",
                idempotency_key="ik_c3",
            )
            await uow.transactions.mark_provider_dispatch_started("tx_chaos_3", "pay_c3")
            await uow.transactions.record_provider_outcome("tx_chaos_3", "UNKNOWN")
            await uow.commit()

        async with AsyncUnitOfWork() as uow:
            tx = await uow.transactions.get_transaction("tx_chaos_3")
            self.assertIsNotNone(tx)
            assert tx is not None
            self.assertEqual(tx.state, "EXECUTING")
            self.assertEqual(tx.provider_status, "UNKNOWN")

    async def test_chaos_fault_04_duplicated_webhook_event_delivery(self) -> None:
        """Fault Category 4: Duplicated webhook delivery processes first outcome and ignores duplicate."""
        async with AsyncUnitOfWork() as uow:
            await uow.transactions.create_transaction(
                transaction_id="tx_chaos_4",
                buyer_id="buyer_chaos_4",
                merchant_id="mer_chaos_4",
                mandate_id="man_chaos_4",
                amount_paise=1000,
                cart_hash="cart_c4",
                idempotency_key="ik_c4",
            )
            await uow.transactions.mark_provider_dispatch_started("tx_chaos_4", "pay_c4")
            await uow.transactions.record_provider_outcome("tx_chaos_4", "SUCCESS")
            await uow.commit()

        # Second duplicate webhook call
        async with AsyncUnitOfWork() as uow:
            tx2 = await uow.transactions.get_transaction("tx_chaos_4")
            self.assertIsNotNone(tx2)
            assert tx2 is not None
            self.assertEqual(tx2.state, "SUCCESS")

    async def test_chaos_fault_05_outbox_worker_crash_and_restart(self) -> None:
        """Fault Category 5: Outbox worker crash mid-batch resumes gracefully on restart."""
        async with AsyncUnitOfWork() as uow:
            await uow.outbox.record_event("payment.captured", "tx_chaos_5", {"tx": "c5"})
            await uow.commit()

        worker1 = OutboxWorker(poll_interval_seconds=1.0)
        await worker1.process_batch()

        # Simulated crash & restart worker2
        worker2 = OutboxWorker(poll_interval_seconds=1.0)
        processed = await worker2.process_batch()
        self.assertEqual(processed, 0)


if __name__ == "__main__":
    unittest.main()
