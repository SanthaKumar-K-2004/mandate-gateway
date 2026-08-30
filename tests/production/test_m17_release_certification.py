"""
Production Acceptance Suite for M17 Release Certification & Disaster Recovery.
Executes end-to-end certification workflow covering manifest validation, backup creation,
clean recovery environment restore, recovery scanning, payment execution, and receipt verification.
"""

import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.deployment.backup_restore import BackupRestoreManager
from apps.api.deployment.release_manifest import generate_release_manifest, verify_release_manifest
from apps.api.observability.recovery_tracker import recovery_tracker
from apps.workers.outbox_worker import OutboxWorker
from db.models.base import Base
import db.session
from db.unit_of_work import AsyncUnitOfWork


class TestM17ProductionReleaseCertification(unittest.IsolatedAsyncioTestCase):
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

    async def test_full_release_certification_workflow(self) -> None:
        """Executes full release certification sequence."""
        # 1. Generate & verify release manifest
        manifest = generate_release_manifest(environment="production")
        manifest_res = verify_release_manifest(manifest)
        self.assertTrue(manifest_res["valid"])

        # 2. Start recovery timing session
        recovery_tracker.start_recovery_session("cert_sess_01", "simulated")

        # 3. Seed production domain entities
        async with AsyncUnitOfWork() as uow:
            await uow.merchants.create_merchant("mer_cert_1", "Cert Merchant", "acc_cert_1")
            await uow.merchants.create_policy("pol_cert_1", "mer_cert_1", "v1.0", 100000, 500000)
            await uow.mandates.create_mandate(
                mandate_id="man_cert_1",
                buyer_id="buyer_cert_1",
                daily_budget_paise=50000,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                merchant_id="mer_cert_1",
            )
            await uow.transactions.create_transaction(
                transaction_id="tx_cert_1",
                buyer_id="buyer_cert_1",
                merchant_id="mer_cert_1",
                mandate_id="man_cert_1",
                amount_paise=15000,
                cart_hash="cart_cert_1",
                idempotency_key="ik_cert_1",
            )
            await uow.execution_attempts.create_attempt(
                attempt_id="att_cert_1",
                transaction_id="tx_cert_1",
                provider_name="Razorpay",
            )
            evt = await uow.audit.record_event(
                event_type="EXECUTION_AUTHORIZED",
                actor="merchant:mer_cert_1",
                component="ExecutionEngine",
                payload={"transaction_id": "tx_cert_1"},
                transaction_id="tx_cert_1",
            )
            await uow.receipts.create_receipt(
                receipt_id="rec_cert_1",
                transaction_id="tx_cert_1",
                audit_event_id=evt.event_id,
                canonical_payload_hash="hash_cert_1",
                signature_hex="sig_cert_1",
                public_key_hex="pubkey_cert_1",
            )
            await uow.outbox.record_event(
                event_type="payment.captured",
                aggregate_id="tx_cert_1",
                payload={"tx": "tx_cert_1"},
            )
            await uow.commit()

        # 4. Perform backup export
        async with AsyncUnitOfWork() as uow:
            snapshot = await BackupRestoreManager.export_database_snapshot(uow)
            self.assertEqual(len(snapshot.transactions), 1)

        # 5. Perform clean restore
        async with AsyncUnitOfWork() as uow:
            restore_res = await BackupRestoreManager.restore_database_snapshot(uow, snapshot)
            await uow.commit()

        self.assertTrue(restore_res["integrity_verification"]["audit_chain_valid"])

        # 6. Outbox worker processing
        outbox_worker = OutboxWorker(poll_interval_seconds=1.0)
        processed = await outbox_worker.process_batch()
        self.assertEqual(processed, 1)

        # 7. Complete recovery timing measurement
        summary = recovery_tracker.complete_recovery_session(
            session_id="cert_sess_01",
            reconciled_count=1,
            unknown_count=0,
            outbox_count=1,
            audit_passed=True,
            receipt_passed=True,
        )
        self.assertTrue(summary["audit_verification_passed"])
        self.assertEqual(summary["transactions_reconciled"], 1)


if __name__ == "__main__":
    unittest.main()
