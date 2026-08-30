"""
Integration test suite for M17 Backup & Restore Certification.
Executes 13-stage backup export, clean recovery environment restore, and post-restore integrity verification.
"""

import json
import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.deployment.backup_restore import BackupRestoreManager
from db.models.base import Base
from db.models.forensic_event import ForensicEventModel
import db.session
from db.unit_of_work import AsyncUnitOfWork


class TestM17BackupRestoreIntegration(unittest.IsolatedAsyncioTestCase):
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

    async def test_full_13_stage_backup_restore_workflow(self) -> None:
        """Verify full export, clean database wipe, restore, and 13-stage integrity verification."""
        # 1. Seed complete dataset across domain tables
        async with AsyncUnitOfWork() as uow:
            # Merchant & Policy
            await uow.merchants.create_merchant("mer_bak_1", "Backup Merchant", "acc_bak_1")
            await uow.merchants.create_policy("pol_bak_1", "mer_bak_1", "v1.0", 100000, 500000)

            # Mandate
            await uow.mandates.create_mandate(
                mandate_id="man_bak_1",
                buyer_id="buyer_bak_1",
                daily_budget_paise=50000,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                merchant_id="mer_bak_1",
            )

            # Transaction
            await uow.transactions.create_transaction(
                transaction_id="tx_bak_1",
                buyer_id="buyer_bak_1",
                merchant_id="mer_bak_1",
                mandate_id="man_bak_1",
                amount_paise=15000,
                cart_hash="cart_bak_1",
                idempotency_key="idempotency_bak_1",
            )
            # Transition to EXECUTING
            await uow.transactions.mark_provider_dispatch_started("tx_bak_1", "pay_bak_1")

            # Audit event
            evt = await uow.audit.record_event(
                event_type="EXECUTION_AUTHORIZED",
                actor="merchant:mer_bak_1",
                component="ExecutionEngine",
                payload={"transaction_id": "tx_bak_1"},
                transaction_id="tx_bak_1",
            )

            # Receipt
            await uow.receipts.create_receipt(
                receipt_id="rec_bak_1",
                transaction_id="tx_bak_1",
                audit_event_id=evt.event_id,
                canonical_payload_hash="hash_bak_1",
                signature_hex="sig_bak_1",
                public_key_hex="pubkey_bak_1",
            )

            # Outbox
            await uow.outbox.record_event(
                event_type="payment.captured",
                aggregate_id="tx_bak_1",
                payload={"tx": "tx_bak_1"},
            )

            # Forensic event
            fe_model = ForensicEventModel(
                event_id="fe_bak_1",
                event_type="payment.lifecycle_step",
                category="PERSISTENCE",
                severity="INFO",
                outcome="SUCCESS",
                merchant_id="mer_bak_1",
                metadata_json=json.dumps({"transaction_id": "tx_bak_1"}),
                hash_signature="sig_bak_1",
            )
            await uow.forensics.record_event(fe_model)
            await uow.commit()

        # 2. Export snapshot
        async with AsyncUnitOfWork() as uow:
            snapshot = await BackupRestoreManager.export_database_snapshot(uow)
            self.assertEqual(len(snapshot.transactions), 1)
            self.assertEqual(len(snapshot.audit_events), 1)
            self.assertTrue(snapshot.snapshot_checksum)

        # 3. Wipe clean & Restore into clean environment
        async with AsyncUnitOfWork() as uow:
            res = await BackupRestoreManager.restore_database_snapshot(
                uow, snapshot, wipe_existing=True
            )
            await uow.commit()

        # 4. Verify post-restore consistency
        self.assertEqual(res["status"], "RESTORED")
        self.assertTrue(res["integrity_verification"]["all_invariants_pass"])
        self.assertTrue(res["integrity_verification"]["audit_chain_valid"])
        self.assertEqual(res["integrity_verification"]["transactions_count"], 1)
        self.assertEqual(res["integrity_verification"]["executing_transactions_count"], 1)

        # 5. Verify restored transaction & receipt details
        async with AsyncUnitOfWork() as uow:
            restored_tx = await uow.transactions.get_transaction("tx_bak_1")
            self.assertIsNotNone(restored_tx)
            assert restored_tx is not None
            self.assertEqual(restored_tx.state, "EXECUTING")

            restored_rec = await uow.receipts.get_receipt("rec_bak_1")
            self.assertIsNotNone(restored_rec)
            assert restored_rec is not None
            self.assertEqual(restored_rec.signature_hex, "sig_bak_1")


if __name__ == "__main__":
    unittest.main()
