"""
Unit tests for Commerce Reconciliation Engine (M26).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.models import ReconciliationState
from apps.api.commerce.reconciliation import CommerceReconciliationEngine


class TestCommerceReconciliation(unittest.TestCase):
    """CommerceReconciliationEngine test suite."""

    def test_01_reconcile_both_confirmed(self) -> None:
        """Verify reconciliation when both payment and merchant order are confirmed."""
        engine = CommerceReconciliationEngine()

        record = engine.reconcile_transaction(
            purchase_request_id="req_rec_01",
            payment_transaction_id="txn_pay_rec_01",
            merchant_id="mer_cafe_acme",
            buyer_id="buyer_rec_101",
            amount_paise=18000,
            currency="INR",
            merchant_order_id="m_ord_rec_01",
            payment_ledger_status="CAPTURED",
            merchant_ledger_status="ORDER_CONFIRMED",
        )

        self.assertEqual(record.state, ReconciliationState.BOTH_CONFIRMED)
        self.assertTrue(record.payment_verified)
        self.assertTrue(record.order_verified)

    def test_02_reconcile_payment_success_order_unknown(self) -> None:
        """Verify reconciliation state PAYMENT_ONLY when payment is confirmed but order creation is pending."""
        engine = CommerceReconciliationEngine()

        record = engine.reconcile_transaction(
            purchase_request_id="req_rec_02",
            payment_transaction_id="txn_pay_rec_02",
            merchant_id="mer_cafe_acme",
            buyer_id="buyer_rec_101",
            amount_paise=18000,
            currency="INR",
            merchant_order_id="m_ord_rec_02",
            payment_ledger_status="CAPTURED",
            merchant_ledger_status="PENDING",
        )

        self.assertEqual(record.state, ReconciliationState.PAYMENT_ONLY)
        self.assertTrue(record.payment_verified)
        self.assertFalse(record.order_verified)
