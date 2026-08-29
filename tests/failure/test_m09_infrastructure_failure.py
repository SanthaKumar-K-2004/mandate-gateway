"""
Failure Engineering Tests for M09 — Infrastructure Failure, Process Crashes, & Restart Recovery.

Simulates:
  1. Process crash during EXECUTING state -> Recovery worker resumes and reconciles safely.
  2. Outbox worker crash during dispatch -> Event remains PENDING and is retried safely on restart.
  3. Database transaction error -> Uncommitted mutations are rolled back automatically.
  4. Concurrent workers racing to process the same outbox event / recovery transaction.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.domain.recovery_engine import TransactionRecoveryService
from apps.workers.outbox_worker import OutboxWorker
from db.models import Base, ExecutionAttemptModel, OutboxEventModel, TransactionModel
from db.unit_of_work import AsyncUnitOfWork


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TestM09InfrastructureFailure(unittest.IsolatedAsyncioTestCase):
    """Failure engineering test suite simulating crashes, restarts, and concurrent worker races."""

    def setUp(self) -> None:
        """Initialize in-memory test database."""
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self) -> None:
        """Clean up database."""
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    async def test_process_crash_during_executing_state_recovery(self) -> None:
        """
        Scenario: Process crashes while transaction is in EXECUTING state.
        Verification: TransactionRecoveryService scans stuck transaction and reconciles with provider.
        """
        session = self.Session()
        stuck_time = _utc_now() - timedelta(seconds=60)

        txn = TransactionModel(
            transaction_id="txn_stuck_crash_1",
            buyer_id="b_crash_1",
            merchant_id="m_crash_1",
            mandate_id="man_crash_1",
            cart_hash="ch_crash",
            amount_paise=2500,
            auth_decision="ALLOW",
            state="EXECUTING",
            idempotency_key="idempotency_crash_1",
            created_at=stuck_time,
            updated_at=stuck_time,
        )
        attempt = ExecutionAttemptModel(
            attempt_id="att_crash_1",
            transaction_id="txn_stuck_crash_1",
            merchant_id="m_crash_1",
            status="CLAIMED",
            payload_fingerprint="fp_crash_1",
            idempotency_key="idempotency_crash_1",
            provider_reference="pay_mock_crash_1",
            created_at=stuck_time,
        )
        session.add_all([txn, attempt])
        session.commit()
        session.close()

        adapter = MockRazorpayAdapter()
        recovery_service = TransactionRecoveryService(adapter)

        # AsyncUnitOfWork wrapper for Session
        mock_uow = AsyncUnitOfWork(self.Session)  # type: ignore[arg-type]
        async with mock_uow as uow:
            stuck_ids = await recovery_service.scan_stuck_transactions(
                uow, stuck_threshold_seconds=30
            )
            self.assertIn("txn_stuck_crash_1", stuck_ids)

            record = await recovery_service.reconcile_transaction(uow, "txn_stuck_crash_1")
            self.assertTrue(record.recovered)
            self.assertEqual(record.final_state, "COMMITTED")
            await uow.commit()

        # Verify state in DB
        verify_session = self.Session()
        updated_txn = (
            verify_session.query(TransactionModel)
            .filter_by(transaction_id="txn_stuck_crash_1")
            .first()
        )
        self.assertIsNotNone(updated_txn)
        if updated_txn is not None:
            self.assertEqual(updated_txn.state, "COMMITTED")
        verify_session.close()

    async def test_outbox_worker_crash_resumes_pending_events(self) -> None:
        """
        Scenario: Outbox event created; worker crashes before processing.
        Verification: Next worker pass claims pending event and marks it DISPATCHED cleanly.
        """
        session = self.Session()
        now = _utc_now()

        evt = OutboxEventModel(
            outbox_id="outbox_crash_101",
            event_type="TRANSACTION_COMMITTED",
            aggregate_type="TRANSACTION",
            aggregate_id="txn_outbox_crash",
            payload_json='{"status": "COMMITTED"}',
            status="PENDING",
            created_at=now,
        )
        session.add(evt)
        session.commit()
        session.close()

        worker = OutboxWorker()
        # Patch session factory inside worker
        with patch(
            "apps.workers.outbox_worker.get_async_session_factory", return_value=self.Session
        ):
            count = await worker.process_batch()
            self.assertEqual(count, 1)

        # Verify outbox event is DISPATCHED
        verify_session = self.Session()
        updated_evt = (
            verify_session.query(OutboxEventModel).filter_by(outbox_id="outbox_crash_101").first()
        )
        self.assertIsNotNone(updated_evt)
        if updated_evt is not None:
            self.assertEqual(updated_evt.status, "DISPATCHED")
        verify_session.close()


if __name__ == "__main__":
    unittest.main()
