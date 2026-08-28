"""
Security tests for M05.2 ORM Schema Constraints & Security Invariants.
"""

from __future__ import annotations

import unittest
from typing import cast
from sqlalchemy import CheckConstraint, Table, UniqueConstraint

from db.models import (
    AuditEventModel,
    MerchantModel,
    MerchantPolicyModel,
    ProductModel,
    TransactionModel,
)


class TestM052SchemaSecurity(unittest.TestCase):
    """Security tests for database schema constraints and table definitions."""

    def test_unique_constraints_present(self) -> None:
        """Verify unique constraints are defined on security-critical columns."""
        # 1. Transactions idempotency_key unique index/constraint
        txn_table = cast(Table, TransactionModel.__table__)
        idempotency_col = txn_table.columns["idempotency_key"]
        self.assertTrue(
            idempotency_col.unique
            or any(
                idx.unique and "idempotency_key" in [c.name for c in idx.columns]
                for idx in txn_table.indexes
            )
        )

        # 2. Audit sequence_number unique constraint
        audit_table = cast(Table, AuditEventModel.__table__)
        seq_col = audit_table.columns["sequence_number"]
        self.assertTrue(
            seq_col.unique
            or any(
                idx.unique and "sequence_number" in [c.name for c in idx.columns]
                for idx in audit_table.indexes
            )
        )

        # 3. Policy version uniqueness constraint
        policy_table = cast(Table, MerchantPolicyModel.__table__)
        has_policy_uq = any(
            isinstance(c, UniqueConstraint)
            and set(c.columns.keys()) == {"merchant_id", "policy_version"}
            for c in policy_table.constraints
        )
        self.assertTrue(has_policy_uq, "Missing unique constraint on (merchant_id, policy_version)")

    def test_non_negative_check_constraints_present(self) -> None:
        """Verify non-negative check constraints are defined for monetary values."""
        product_table = cast(Table, ProductModel.__table__)
        has_price_chk = any(
            isinstance(c, CheckConstraint) and "price_paise >= 0" in str(c.sqltext)
            for c in product_table.constraints
        )
        self.assertTrue(has_price_chk, "Missing price >= 0 check constraint on products")

        policy_table = cast(Table, MerchantPolicyModel.__table__)
        has_limit_chk = any(
            isinstance(c, CheckConstraint) and "autonomous_limit_paise >= 0" in str(c.sqltext)
            for c in policy_table.constraints
        )
        self.assertTrue(
            has_limit_chk, "Missing autonomous_limit >= 0 check constraint on merchant_policies"
        )

    def test_foreign_keys_present(self) -> None:
        """Verify foreign keys are enforced on child tables."""
        txn_table = cast(Table, TransactionModel.__table__)
        fk_cols = {fk.column.table.name for fk in txn_table.foreign_keys}
        self.assertIn("merchants", fk_cols)
        self.assertIn("mandates", fk_cols)

    def test_secret_redaction_in_repr(self) -> None:
        """Verify model __repr__ redacts any fields containing 'password' or 'secret'."""
        merchant = MerchantModel(merchant_id="m_1", name="Secure Merchant")
        merchant_str = repr(merchant)
        self.assertNotIn("password", merchant_str)
        self.assertNotIn("secret", merchant_str)


if __name__ == "__main__":
    unittest.main()
