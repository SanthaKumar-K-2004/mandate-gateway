"""
Unit tests for Order Verification Engine (M24).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.models import OrderStatus
from apps.api.commerce.order_verification import OrderVerificationEngine


class TestOrderVerification(unittest.TestCase):
    """Order Verification Engine test suite."""

    def test_01_order_intent_recorded(self) -> None:
        """Verify recording initial checkout intent sets status to ORDER_PENDING."""
        engine = OrderVerificationEngine()
        outcome = engine.record_checkout_intent(
            preparation_id="prep_101",
            request_id="req_101",
            merchant_id="mer_test",
            capability_str="CHECKOUT_HANDOFF",
        )
        self.assertEqual(outcome.order_status, OrderStatus.ORDER_PENDING)
        self.assertEqual(outcome.preparation_id, "prep_101")

    def test_02_order_outcome_verification_technical_honesty(self) -> None:
        """Verify payment authorization without merchant order proof remains ORDER_UNKNOWN."""
        engine = OrderVerificationEngine()
        outcome = engine.record_checkout_intent(
            "prep_102", "req_102", "mer_test", "CHECKOUT_HANDOFF"
        )

        # Verify without authoritative evidence
        updated = engine.verify_order_outcome(
            outcome_id=outcome.outcome_id,
            payment_transaction_id="txn_razorpay_99",
            merchant_order_id=None,
            authoritative_evidence=None,
        )
        # TECHNICAL HONESTY: Must be ORDER_UNKNOWN, not ORDER_VERIFIED!
        self.assertEqual(updated.order_status, OrderStatus.ORDER_UNKNOWN)

    def test_03_order_outcome_verified_with_evidence(self) -> None:
        """Verify order with authoritative evidence transitions to ORDER_VERIFIED."""
        engine = OrderVerificationEngine()
        outcome = engine.record_checkout_intent("prep_103", "req_103", "mer_test", "VERIFIED_API")

        authoritative = {
            "amount_paise": "48000",
            "currency": "INR",
            "source": "connector_cafe_acme_api",
        }
        updated = engine.verify_order_outcome(
            outcome_id=outcome.outcome_id,
            payment_transaction_id="txn_razorpay_100",
            merchant_order_id="m_ord_acme_88",
            authoritative_evidence=authoritative,
        )
        self.assertEqual(updated.order_status, OrderStatus.ORDER_VERIFIED)
        self.assertIsNotNone(updated.order_evidence)
        assert updated.order_evidence is not None
        self.assertEqual(updated.order_evidence.merchant_order_id, "m_ord_acme_88")
