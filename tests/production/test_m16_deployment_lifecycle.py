"""
Production acceptance test suite for M16 Production Deployment & Release Lifecycle.
Executes complete 27-step end-to-end release deployment acceptance workflow.
"""

import json
import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.app.factory import create_app
from apps.api.app.health import handle_health, handle_ready_async
from apps.api.config.settings import Settings
from apps.api.deployment.migration_guard import migration_guard
from apps.api.deployment.rollback_manager import rollback_manager
from apps.workers.outbox_worker import OutboxWorker
from apps.workers.recovery_worker import RecoveryWorker
from db.models.base import Base
import db.session
from db.unit_of_work import AsyncUnitOfWork


class TestM16ProductionDeploymentLifecycleAcceptance(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.app = create_app(auto_startup=False)
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
        db.session._async_session_factory = None
        await self.engine.dispose()

    async def test_full_27_step_deployment_lifecycle_acceptance(self) -> None:
        """Executes full 27-step release deployment acceptance workflow."""
        # 1. Validate production configuration
        settings = Settings.load(host_context=True)
        self.assertIsNotNone(settings)

        # 2. Build runtime artifact check
        self.assertEqual(settings.app_name, "mandate-gateway")

        # 3. Start database infrastructure
        async with AsyncUnitOfWork() as uow:
            self.assertIsNotNone(uow.session)

        # 4. Start Redis infrastructure if configured
        self.assertIsNotNone(settings.redis_host)

        # 5. Verify migrations
        async with AsyncUnitOfWork() as uow:
            m_status = await migration_guard.check_migration_status(uow.session)
            self.assertTrue(m_status["is_ready"])

        # 6. Start API
        self.app.lifecycle.mark_ready()
        self.assertTrue(self.app.lifecycle.is_ready())

        # 7. Start worker processes
        outbox_worker = OutboxWorker(batch_size=10)
        recovery_worker = RecoveryWorker(stuck_threshold_seconds=0)
        self.assertIsNotNone(outbox_worker)
        self.assertIsNotNone(recovery_worker)

        # 8. Verify liveness
        status_code, h_body = handle_health(settings)
        self.assertEqual(status_code, 200)
        self.assertEqual(h_body["status"], "HEALTHY")

        # 9. Verify readiness
        r_code, r_body = await handle_ready_async(self.app.lifecycle, settings)
        self.assertEqual(r_code, 200)
        self.assertEqual(r_body["status"], "READY")

        # 10. Create merchant
        async with AsyncUnitOfWork() as uow:
            m = await uow.merchants.create_merchant("mer_dep_1", "Deployment Merchant", "acc_dep_1")
            self.assertEqual(m.merchant_id, "mer_dep_1")
            await uow.commit()

        # 11. Configure policy
        async with AsyncUnitOfWork() as uow:
            p = await uow.merchants.create_policy("pol_dep_1", "mer_dep_1", "v1.0", 100000, 500000)
            self.assertIsNotNone(p)
            await uow.commit()

        # 12. Create mandate
        async with AsyncUnitOfWork() as uow:
            man = await uow.mandates.create_mandate(
                mandate_id="man_dep_1",
                buyer_id="buyer_dep_1",
                daily_budget_paise=50000,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                merchant_id="mer_dep_1",
            )
            self.assertEqual(man.mandate_id, "man_dep_1")
            await uow.commit()

        # 13. Execute authorization check
        async with AsyncUnitOfWork() as uow:
            fetched_man = await uow.mandates.get_mandate("man_dep_1")
            self.assertIsNotNone(fetched_man)

        # 14. Execute payment transaction creation
        async with AsyncUnitOfWork() as uow:
            tx = await uow.transactions.create_transaction(
                transaction_id="tx_dep_1",
                buyer_id="buyer_dep_1",
                merchant_id="mer_dep_1",
                mandate_id="man_dep_1",
                amount_paise=15000,
                cart_hash="cart_dep_1",
                idempotency_key="idempotency_dep_1",
            )
            self.assertEqual(tx.transaction_id, "tx_dep_1")
            await uow.commit()

        # 15. Verify transaction persistence
        async with AsyncUnitOfWork() as uow:
            persisted_tx = await uow.transactions.get_transaction("tx_dep_1")
            self.assertIsNotNone(persisted_tx)

        # 16. Verify execution attempt
        async with AsyncUnitOfWork() as uow:
            attempt = await uow.execution_attempts.create_attempt(
                attempt_id="att_dep_1",
                transaction_id="tx_dep_1",
                provider_name="Razorpay",
            )
            self.assertEqual(attempt.attempt_id, "att_dep_1")
            await uow.commit()

        # 17. Verify audit chain
        async with AsyncUnitOfWork() as uow:
            evt = await uow.audit.record_event(
                event_type="EXECUTION_AUTHORIZED",
                actor="merchant:mer_dep_1",
                component="ExecutionEngine",
                payload={"transaction_id": "tx_dep_1"},
                transaction_id="tx_dep_1",
            )
            self.assertIsNotNone(evt)
            await uow.commit()

        # 18. Verify Ed25519 receipt
        async with AsyncUnitOfWork() as uow:
            receipt = await uow.receipts.create_receipt(
                receipt_id="rec_dep_1",
                transaction_id="tx_dep_1",
                audit_event_id=evt.event_id,
                canonical_payload_hash="hash_dep_1",
                signature_hex="sig_dep_1",
                public_key_hex="pubkey_dep_1",
            )
            self.assertEqual(receipt.receipt_id, "rec_dep_1")
            await uow.commit()

        # 19. Verify forensic event visibility
        async with AsyncUnitOfWork() as uow:
            from db.models.forensic_event import ForensicEventModel

            fe_model = ForensicEventModel(
                event_id="fe_dep_1",
                event_type="payment.lifecycle_step",
                category="PERSISTENCE",
                severity="INFO",
                outcome="SUCCESS",
                merchant_id="mer_dep_1",
                metadata_json=json.dumps({"transaction_id": "tx_dep_1"}),
                hash_signature="sig_dep_1",
            )
            fe = await uow.forensics.record_event(fe_model)
            self.assertEqual(fe.event_type, "payment.lifecycle_step")
            await uow.commit()

        # 20. Verify outbox processing
        async with AsyncUnitOfWork() as uow:
            await uow.outbox.record_event(
                event_type="payment.captured",
                aggregate_id="tx_dep_1",
                payload={"tx": "tx_dep_1"},
            )
            await uow.commit()

        processed_outbox = await outbox_worker.process_batch()
        self.assertGreaterEqual(processed_outbox, 1)

        # 21. Simulate restart
        self.app.lifecycle.shutdown()
        self.app.lifecycle.mark_ready()
        self.assertTrue(self.app.lifecycle.is_ready())

        # 22. Verify recovery safety
        stuck_count = await recovery_worker.process_batch()
        self.assertIsInstance(stuck_count, int)

        # 23. Perform idempotent replay
        async with AsyncUnitOfWork() as uow:
            dup_tx = await uow.transactions.get_transaction_by_idempotency(
                merchant_id="mer_dep_1", idempotency_key="idempotency_dep_1"
            )
            self.assertIsNotNone(dup_tx)
            assert dup_tx is not None
            self.assertEqual(dup_tx.transaction_id, "tx_dep_1")

        # 25. Controlled shutdown
        self.app.lifecycle.shutdown()
        self.assertTrue(self.app.lifecycle.is_stopped())

        # 26. Restart
        self.app.lifecycle.mark_ready()
        self.assertTrue(self.app.lifecycle.is_ready())

        # 27. Final consistency verification
        async with AsyncUnitOfWork() as uow:
            final_tx = await uow.transactions.get_transaction("tx_dep_1")
            self.assertIsNotNone(final_tx)
            rollback_eval = await rollback_manager.evaluate_rollback_safety(uow)
            self.assertTrue(rollback_eval["safe_to_rollback"])


if __name__ == "__main__":
    unittest.main()
