"""
Integration tests for M05.2 Database Schema Creation & Migration Reproducibility.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from db.models import (
    AuditEventModel,
    Base,
    MandateModel,
    MerchantModel,
    MerchantPolicyModel,
    ProductModel,
    TransactionModel,
)


class TestM052MigrationsIntegration(unittest.TestCase):
    """Integration tests for database schema creation and constraint enforcement."""

    def setUp(self) -> None:
        """Create an in-memory SQLite database and build all tables."""
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self) -> None:
        """Drop all tables after test."""
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_schema_creation_and_entity_insertion(self) -> None:
        """Verify all tables are created cleanly and valid entities can be inserted."""
        session = self.Session()
        now = datetime.now(timezone.utc)

        # 1. Insert Merchant
        merchant = MerchantModel(
            merchant_id="m_100",
            name="Acme Corp",
            razorpay_account_id="acc_acme_1",
            active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(merchant)

        # 2. Insert Policy
        policy = MerchantPolicyModel(
            id="pol_100",
            merchant_id="m_100",
            policy_version="v1",
            autonomous_limit_paise=5000,
            step_up_threshold_paise=10000,
            allowed_categories_json='["electronics"]',
            allowed_operations_json='["PAYMENT"]',
            blocked_operations_json="[]",
            effective_at=now,
            created_at=now,
        )
        session.add(policy)

        # 3. Insert Product
        product = ProductModel(
            product_id="prod_100",
            merchant_id="m_100",
            name="Laptop",
            price_paise=4500,
            currency="INR",
            category="electronics",
            active=True,
            created_at=now,
        )
        session.add(product)

        # 4. Insert Mandate
        mandate = MandateModel(
            mandate_id="mandate_100",
            buyer_id="buyer_100",
            merchant_id="m_100",
            category_scope="electronics",
            daily_budget_paise=10000,
            currency="INR",
            region="IN",
            status="ACTIVE",
            expires_at=now,
            created_at=now,
        )
        session.add(mandate)

        # 5. Insert Transaction
        txn = TransactionModel(
            transaction_id="txn_100",
            buyer_id="buyer_100",
            merchant_id="m_100",
            mandate_id="mandate_100",
            cart_hash="hash_100",
            amount_paise=4500,
            currency="INR",
            region="IN",
            auth_decision="ALLOW",
            state="EXECUTED",
            idempotency_key="idempotency_100",
            created_at=now,
            updated_at=now,
        )
        session.add(txn)

        # 6. Insert Audit Event
        audit = AuditEventModel(
            event_id="evt_100",
            sequence_number=1,
            event_type="TRANSACTION_AUTHORIZED",
            transaction_id="txn_100",
            mandate_id="mandate_100",
            merchant_id="m_100",
            buyer_id="buyer_100",
            payload_json='{"status":"ALLOW"}',
            previous_hash="0" * 64,
            event_hash="a" * 64,
            timestamp=now,
        )
        session.add(audit)

        session.commit()

        # Query back
        fetched_merchant = session.query(MerchantModel).filter_by(merchant_id="m_100").first()
        self.assertIsNotNone(fetched_merchant)
        assert fetched_merchant is not None
        self.assertEqual(len(fetched_merchant.products), 1)
        self.assertEqual(fetched_merchant.products[0].name, "Laptop")
        session.close()

    def test_duplicate_idempotency_key_rejected(self) -> None:
        """Verify unique constraint on idempotency_key rejects duplicate insertions."""
        session = self.Session()
        now = datetime.now(timezone.utc)

        merchant = MerchantModel(
            merchant_id="m_200", name="Merchant 2", active=True, created_at=now, updated_at=now
        )
        mandate = MandateModel(
            mandate_id="man_200",
            buyer_id="b_200",
            daily_budget_paise=5000,
            status="ACTIVE",
            expires_at=now,
            created_at=now,
        )
        session.add_all([merchant, mandate])
        session.commit()

        txn1 = TransactionModel(
            transaction_id="txn_201",
            buyer_id="b_200",
            merchant_id="m_200",
            mandate_id="man_200",
            cart_hash="h1",
            amount_paise=1000,
            auth_decision="ALLOW",
            state="EXECUTED",
            idempotency_key="DUPLICATE_KEY",
            created_at=now,
            updated_at=now,
        )
        txn2 = TransactionModel(
            transaction_id="txn_202",
            buyer_id="b_200",
            merchant_id="m_200",
            mandate_id="man_200",
            cart_hash="h2",
            amount_paise=1000,
            auth_decision="ALLOW",
            state="EXECUTED",
            idempotency_key="DUPLICATE_KEY",
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


if __name__ == "__main__":
    unittest.main()
