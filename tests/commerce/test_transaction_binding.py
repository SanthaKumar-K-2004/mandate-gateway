"""
Unit tests for 1:1 Payment ↔ Merchant Order Transaction Binding (M25).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.transaction_binding import (
    CommerceTransactionBindingManager,
    TransactionBindingError,
)


class TestTransactionBinding(unittest.TestCase):
    """CommerceTransactionBindingManager test suite."""

    def test_01_successful_1to1_binding(self) -> None:
        """Verify successful 1:1 payment transaction to merchant order binding."""
        mgr = CommerceTransactionBindingManager()

        binding = mgr.bind_transaction_to_order(
            binding_id="bind_01",
            razorpay_transaction_id="txn_razorpay_101",
            merchant_order_id="m_ord_acme_101",
            merchant_id="mer_cafe_acme",
            product_id="prod_tea_01",
            product_evidence_hash="ev_hash_101",
            order_binding_hash="ord_hash_101",
            payment_amount_paise=14000,
            currency="INR",
            connector_id="connector_cafe_acme_api",
        )

        self.assertEqual(binding.razorpay_transaction_id, "txn_razorpay_101")
        self.assertEqual(binding.merchant_order_id, "m_ord_acme_101")

        # Verify dual lookups
        b1 = mgr.get_binding_by_transaction("txn_razorpay_101")
        self.assertIsNotNone(b1)
        self.assertEqual(b1.merchant_order_id, "m_ord_acme_101")  # type: ignore

        b2 = mgr.get_binding_by_order("m_ord_acme_101")
        self.assertIsNotNone(b2)
        self.assertEqual(b2.razorpay_transaction_id, "txn_razorpay_101")  # type: ignore

    def test_02_duplicate_transaction_rebinding_rejected(self) -> None:
        """Verify attempting to bind an existing transaction ID to a different order is rejected."""
        mgr = CommerceTransactionBindingManager()

        mgr.bind_transaction_to_order(
            binding_id="bind_01",
            razorpay_transaction_id="txn_razorpay_101",
            merchant_order_id="m_ord_acme_101",
            merchant_id="mer_cafe_acme",
            product_id="prod_tea_01",
            product_evidence_hash="ev_hash_101",
            order_binding_hash="ord_hash_101",
            payment_amount_paise=14000,
            currency="INR",
            connector_id="connector_cafe_acme_api",
        )

        with self.assertRaises(TransactionBindingError):
            mgr.bind_transaction_to_order(
                binding_id="bind_02",
                razorpay_transaction_id="txn_razorpay_101",  # Same payment transaction!
                merchant_order_id="m_ord_acme_999",  # Different order!
                merchant_id="mer_cafe_acme",
                product_id="prod_tea_01",
                product_evidence_hash="ev_hash_101",
                order_binding_hash="ord_hash_101",
                payment_amount_paise=14000,
                currency="INR",
                connector_id="connector_cafe_acme_api",
            )
