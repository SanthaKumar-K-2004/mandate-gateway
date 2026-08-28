"""
Unit tests for M05.2 ORM Data Models & Metadata.
"""

from __future__ import annotations

import unittest

from db.models import (
    Base,
    MerchantModel,
    MerchantPolicyModel,
    TransactionModel,
)


class TestM052ModelsUnit(unittest.TestCase):
    """Unit tests for SQLAlchemy 2.0 ORM data models."""

    def test_metadata_contains_all_11_tables(self) -> None:
        """Verify Base.metadata registers all 11 expected tables."""
        tables = set(Base.metadata.tables.keys())
        expected = {
            "merchants",
            "merchant_policies",
            "products",
            "mandates",
            "transactions",
            "budget_reservations",
            "step_up_challenges",
            "replay_records",
            "nonce_records",
            "audit_events",
            "action_receipts",
        }
        self.assertTrue(expected.issubset(tables), f"Missing tables: {expected - tables}")

    def test_merchant_model_instantiation(self) -> None:
        """Verify MerchantModel instantiation and fields."""
        merchant = MerchantModel(
            merchant_id="merchant_test_101",
            name="Test Merchant",
            razorpay_account_id="acc_12345",
            active=True,
        )
        self.assertEqual(merchant.merchant_id, "merchant_test_101")
        self.assertEqual(merchant.name, "Test Merchant")
        self.assertIn("merchant_test_101", repr(merchant))

    def test_policy_model_instantiation(self) -> None:
        """Verify MerchantPolicyModel fields and structure."""
        policy = MerchantPolicyModel(
            id="pol_001",
            merchant_id="merchant_test_101",
            policy_version="v1.0",
            autonomous_limit_paise=5000,
            step_up_threshold_paise=10000,
            allowed_categories_json='["electronics"]',
            allowed_operations_json='["PAYMENT"]',
            blocked_operations_json="[]",
        )
        self.assertEqual(policy.autonomous_limit_paise, 5000)
        self.assertEqual(policy.merchant_id, "merchant_test_101")

    def test_transaction_model_instantiation(self) -> None:
        """Verify TransactionModel fields and idempotency key constraint configuration."""
        txn = TransactionModel(
            transaction_id="txn_001",
            buyer_id="buyer_001",
            merchant_id="merchant_test_101",
            mandate_id="mandate_001",
            cart_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            amount_paise=2500,
            auth_decision="ALLOW",
            state="EXECUTED",
            idempotency_key="idempotency_key_123",
        )
        self.assertEqual(txn.amount_paise, 2500)
        self.assertEqual(txn.auth_decision, "ALLOW")


if __name__ == "__main__":
    unittest.main()
