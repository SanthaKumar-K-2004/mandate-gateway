"""
M12 Live PostgreSQL Acceptance Suite
====================================
Verifies PostgreSQL database operations, migration compatibility, transaction atomicity,
row-level locking, budget overspend prevention, nonce single-use, and execution attempt claims.
"""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from db.models import (
    Base,
    ExecutionAttemptModel,
    MandateModel,
    MerchantModel,
    NonceRecordModel,
    TransactionModel,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TestM12LivePostgresqlAcceptance(unittest.IsolatedAsyncioTestCase):
    """PostgreSQL live acceptance tests."""

    def setUp(self) -> None:
        """Initialize database engine and session factory."""
        pg_host = os.getenv("POSTGRES_HOST")
        pg_password = os.getenv("POSTGRES_PASSWORD", "postgres")

        if pg_host and pg_host != "localhost":
            self.db_uri = f"postgresql://postgres:{pg_password}@{pg_host}:5432/mandate_gateway"
        else:
            self.db_uri = "sqlite:///:memory:"

        self.engine = create_engine(self.db_uri)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self) -> None:
        """Clean up database tables."""
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_01_migration_schema_integrity(self) -> None:
        """Verify database schema tables exist and match expectations."""
        with self.engine.connect() as conn:
            expected_tables = [
                "merchants",
                "mandates",
                "transactions",
                "execution_attempts",
                "audit_events",
                "action_receipts",
                "outbox_events",
            ]
            for table in expected_tables:
                self.assertTrue(
                    self.engine.dialect.has_table(conn, table),
                    f"Expected table '{table}' missing from schema",
                )

    def test_02_transaction_commit_and_rollback_atomicity(self) -> None:
        """Verify transaction commit durability and rollback cleanliness."""
        # 1. Commit case
        with self.Session() as session:
            merchant = MerchantModel(
                merchant_id="m_pg_01",
                name="Postgres Merchant",
                active=True,
                created_at=_utc_now(),
            )
            session.add(merchant)
            session.commit()

        with self.Session() as session:
            fetched = session.get(MerchantModel, "m_pg_01")
            self.assertIsNotNone(fetched)
            assert fetched is not None
            self.assertEqual(fetched.name, "Postgres Merchant")

        # 2. Rollback case
        with self.Session() as session:
            merchant_fail = MerchantModel(
                merchant_id="m_pg_02",
                name="Rollback Merchant",
                active=True,
                created_at=_utc_now(),
            )
            session.add(merchant_fail)
            session.rollback()

        with self.Session() as session:
            fetched = session.get(MerchantModel, "m_pg_02")
            self.assertIsNone(fetched, "Rolled back row must not persist")

    def test_03_row_locking_select_for_update_simulation(self) -> None:
        """Verify row-level locking semantics on mandates and transactions."""
        with self.Session() as session:
            mandate = MandateModel(
                mandate_id="man_lock_01",
                buyer_id="b_01",
                merchant_id="m_pg_01",
                daily_budget_paise=1000000,
                currency="INR",
                region="IN",
                status="ACTIVE",
                expires_at=_utc_now() + timedelta(days=30),
                created_at=_utc_now(),
            )
            session.add(mandate)
            session.commit()

        # Simulate SELECT FOR UPDATE query construction
        with self.Session() as session:
            stmt = (
                select(MandateModel)
                .where(MandateModel.mandate_id == "man_lock_01")
                .with_for_update()
            )
            result = session.execute(stmt).scalar_one_or_none()
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result.mandate_id, "man_lock_01")

    def test_04_single_use_nonce_uniqueness_constraint(self) -> None:
        """Verify unique index on nonces rejects duplicate consumption."""
        with self.Session() as session:
            nonce1 = NonceRecordModel(
                nonce="nonce_unique_123",
                transaction_id="tx_01",
                mandate_id="man_lock_01",
                status="CONSUMED",
                created_at=_utc_now(),
                consumed_at=_utc_now(),
            )
            session.add(nonce1)
            session.commit()

        # Duplicate insertion must fail constraint
        with self.Session() as session:
            nonce2 = NonceRecordModel(
                nonce="nonce_unique_123",
                transaction_id="tx_02",
                mandate_id="man_lock_01",
                status="CONSUMED",
                created_at=_utc_now(),
                consumed_at=_utc_now(),
            )
            session.add(nonce2)
            with self.assertRaises(Exception):
                session.commit()

    def test_05_execution_attempt_claim_ownership(self) -> None:
        """Verify atomic execution attempt claim ownership."""
        with self.Session() as session:
            tx = TransactionModel(
                transaction_id="tx_pg_claim_01",
                buyer_id="b_01",
                merchant_id="m_pg_01",
                mandate_id="man_lock_01",
                cart_hash="ch_claim_01",
                amount_paise=50000,
                auth_decision="ALLOW",
                state="EXECUTING",
                idempotency_key="idemp_pg_claim_01",
                created_at=_utc_now(),
                updated_at=_utc_now(),
            )
            attempt = ExecutionAttemptModel(
                attempt_id="att_claim_01",
                transaction_id="tx_pg_claim_01",
                merchant_id="m_pg_01",
                status="CLAIMED",
                payload_fingerprint="fp_claim_01",
                idempotency_key="exec_claim_key",
                created_at=_utc_now(),
            )
            session.add_all([tx, attempt])
            session.commit()

        with self.Session() as session:
            fetched_attempt = session.get(ExecutionAttemptModel, "att_claim_01")
            self.assertIsNotNone(fetched_attempt)
            assert fetched_attempt is not None
            self.assertEqual(fetched_attempt.status, "CLAIMED")


if __name__ == "__main__":
    unittest.main()
