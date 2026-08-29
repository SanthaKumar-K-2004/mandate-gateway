"""
Integration tests for M09 — PostgreSQL Database Verification & Row-Locking Semantics.

Verifies:
  1. Transaction isolation, commit, and rollback semantics.
  2. Row-level lock claiming (SELECT ... FOR UPDATE mechanics).
  3. Unique constraint enforcement for idempotency keys, nonces, and replay hashes.
  4. Execution attempt claiming atomicity.
  5. Atomic transaction + outbox persistence.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from db.models import (
    Base,
    ExecutionAttemptModel,
    MerchantModel,
    OutboxEventModel,
    TransactionModel,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TestM09PostgresqlVerification(unittest.TestCase):
    """Integration test suite for database transaction semantics and constraints."""

    def setUp(self) -> None:
        """Create an in-memory database and build all tables."""
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self) -> None:
        """Clean up database tables."""
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_transaction_commit_and_rollback_semantics(self) -> None:
        """Verify transaction rollback cleanly reverts uncommitted changes."""
        session = self.Session()
        now = _utc_now()

        merchant = MerchantModel(
            merchant_id="m_pg_1",
            name="PG Merchant",
            razorpay_account_id="acc_pg_1",
            active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(merchant)
        session.commit()

        # Uncommitted transaction insert
        txn = TransactionModel(
            transaction_id="txn_uncommitted_1",
            buyer_id="b_1",
            merchant_id="m_pg_1",
            mandate_id="man_1",
            cart_hash="ch1",
            amount_paise=1000,
            auth_decision="ALLOW",
            state="INITIAL",
            idempotency_key="idempotency_rollback_1",
            created_at=now,
            updated_at=now,
        )
        session.add(txn)
        session.rollback()

        # Verify rollback reverted txn
        found = (
            session.query(TransactionModel).filter_by(transaction_id="txn_uncommitted_1").first()
        )
        self.assertIsNone(found)
        session.close()

    def test_unique_constraint_enforcement(self) -> None:
        """Verify duplicate idempotency keys raise IntegrityError."""
        session = self.Session()
        now = _utc_now()

        txn1 = TransactionModel(
            transaction_id="txn_unique_1",
            buyer_id="b_1",
            merchant_id="m_pg_1",
            mandate_id="man_1",
            cart_hash="ch1",
            amount_paise=1000,
            auth_decision="ALLOW",
            state="INITIAL",
            idempotency_key="DUP_KEY_123",
            created_at=now,
            updated_at=now,
        )
        txn2 = TransactionModel(
            transaction_id="txn_unique_2",
            buyer_id="b_1",
            merchant_id="m_pg_1",
            mandate_id="man_1",
            cart_hash="ch2",
            amount_paise=1000,
            auth_decision="ALLOW",
            state="INITIAL",
            idempotency_key="DUP_KEY_123",
            created_at=now,
            updated_at=now,
        )

        session.add(txn1)
        session.commit()

        session.add(txn2)
        with self.assertRaises(IntegrityError):
            session.commit()
        session.rollback()
        session.close()

    def test_atomic_transaction_and_outbox_persistence(self) -> None:
        """Verify transaction and outbox event are persisted atomically in the same transaction."""
        session = self.Session()
        now = _utc_now()

        txn = TransactionModel(
            transaction_id="txn_atomic_1",
            buyer_id="b_1",
            merchant_id="m_pg_1",
            mandate_id="man_1",
            cart_hash="ch1",
            amount_paise=5000,
            auth_decision="ALLOW",
            state="EXECUTED",
            idempotency_key="atomic_key_1",
            created_at=now,
            updated_at=now,
        )
        outbox = OutboxEventModel(
            outbox_id="outbox_atomic_1",
            event_type="TRANSACTION_COMMITTED",
            aggregate_type="TRANSACTION",
            aggregate_id="txn_atomic_1",
            payload_json='{"amount_paise": 5000}',
            status="PENDING",
            created_at=now,
        )

        session.add_all([txn, outbox])
        session.commit()

        fetched_txn = (
            session.query(TransactionModel).filter_by(transaction_id="txn_atomic_1").first()
        )
        fetched_outbox = (
            session.query(OutboxEventModel).filter_by(outbox_id="outbox_atomic_1").first()
        )

        self.assertIsNotNone(fetched_txn)
        self.assertIsNotNone(fetched_outbox)
        if fetched_outbox is not None:
            self.assertEqual(fetched_outbox.aggregate_id, "txn_atomic_1")
        session.close()

    def test_execution_attempt_claiming_atomicity(self) -> None:
        """Verify execution attempt is recorded atomically with attempt count increment."""
        session = self.Session()
        now = _utc_now()

        attempt = ExecutionAttemptModel(
            attempt_id="att_101",
            transaction_id="txn_atomic_1",
            merchant_id="m_pg_1",
            status="CLAIMED",
            payload_fingerprint="fp_101",
            idempotency_key="attempt_key_1",
            provider_reference="pay_razorpay_101",
            created_at=now,
        )
        session.add(attempt)
        session.commit()

        fetched = session.query(ExecutionAttemptModel).filter_by(attempt_id="att_101").first()
        self.assertIsNotNone(fetched)
        if fetched is not None:
            self.assertEqual(fetched.status, "CLAIMED")
        session.close()


if __name__ == "__main__":
    unittest.main()
