"""
Unit tests for Cryptographic Order Binding (M25).
"""

from __future__ import annotations

import unittest
from typing import Any, Dict

from apps.api.commerce.order_binding import CommerceOrderBinder


class TestOrderBinding(unittest.TestCase):
    """CommerceOrderBinder test suite."""

    def test_01_compute_and_verify_binding(self) -> None:
        """Verify HMAC-SHA256 order binding hash computation and verification."""
        binder = CommerceOrderBinder(secret_key="test_binding_secret")

        payload: Dict[str, Any] = {
            "purchase_request_id": "req_88",
            "merchant_id": "mer_cafe_acme",
            "buyer_id": "buyer_101",
            "product_id": "prod_tea_01",
            "quantity": 1,
            "amount_paise": 14000,
            "currency": "INR",
            "merchant_order_id": "m_ord_101",
            "payment_reference": "txn_pay_101",
            "plan_hash": "plan_hash_88",
        }

        binding_hash = binder.compute_binding_hash(
            purchase_request_id=str(payload["purchase_request_id"]),
            merchant_id=str(payload["merchant_id"]),
            buyer_id=str(payload["buyer_id"]),
            product_id=str(payload["product_id"]),
            quantity=int(str(payload["quantity"])),
            amount_paise=int(str(payload["amount_paise"])),
            currency=str(payload["currency"]),
            merchant_order_id=str(payload["merchant_order_id"]),
            payment_reference=str(payload["payment_reference"]),
            plan_hash=str(payload["plan_hash"]),
        )

        self.assertTrue(binder.verify_binding(payload, binding_hash))

    def test_02_detect_tampered_payload(self) -> None:
        """Verify tampered payload (product or amount substitution) fails binding verification."""
        binder = CommerceOrderBinder(secret_key="test_binding_secret")

        payload: Dict[str, Any] = {
            "purchase_request_id": "req_88",
            "merchant_id": "mer_cafe_acme",
            "buyer_id": "buyer_101",
            "product_id": "prod_tea_01",
            "quantity": 1,
            "amount_paise": 14000,
            "currency": "INR",
            "merchant_order_id": "m_ord_101",
            "payment_reference": "txn_pay_101",
            "plan_hash": "plan_hash_88",
        }

        original_hash = binder.compute_binding_hash(
            purchase_request_id=str(payload["purchase_request_id"]),
            merchant_id=str(payload["merchant_id"]),
            buyer_id=str(payload["buyer_id"]),
            product_id=str(payload["product_id"]),
            quantity=int(str(payload["quantity"])),
            amount_paise=int(str(payload["amount_paise"])),
            currency=str(payload["currency"]),
            merchant_order_id=str(payload["merchant_order_id"]),
            payment_reference=str(payload["payment_reference"]),
            plan_hash=str(payload["plan_hash"]),
        )

        # Substitution attack: Change product_id
        tampered_product = dict(payload)
        tampered_product["product_id"] = "prod_expensive_02"
        self.assertFalse(binder.verify_binding(tampered_product, original_hash))

        # Substitution attack: Change amount
        tampered_amount = dict(payload)
        tampered_amount["amount_paise"] = 1000
        self.assertFalse(binder.verify_binding(tampered_amount, original_hash))
