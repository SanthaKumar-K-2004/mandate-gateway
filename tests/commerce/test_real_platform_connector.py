"""
Unit tests for Real Platform Commerce Connector (M25).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.connectors.real_platform import RealPlatformConnector
from apps.api.commerce.models import CheckoutCapability
from apps.api.commerce.product_truth_engine import ProductTruthEngine


class TestRealPlatformConnector(unittest.TestCase):
    """RealPlatformConnector test suite."""

    def test_01_supports_domain(self) -> None:
        """Verify supported domain matching."""
        connector = RealPlatformConnector()
        self.assertTrue(connector.supports_domain("cafeacme.local"))
        self.assertTrue(connector.supports_domain("api.cafeacme.local"))
        self.assertFalse(connector.supports_domain("unknown.com"))

    def test_02_capability_declaration(self) -> None:
        """Verify capability is declared as VERIFIED_API."""
        connector = RealPlatformConnector()
        self.assertEqual(connector.capability, CheckoutCapability.VERIFIED_API)

    def test_03_create_cart_checkout_and_order(self) -> None:
        """Verify complete direct merchant API cart, checkout, and order creation flow."""
        connector = RealPlatformConnector()

        cart = connector.create_cart(
            "buyer_101", [{"product_id": "prod_tea_01", "amount_paise": 14000, "quantity": 1}]
        )
        self.assertIn("cart_acme_", cart["cart_id"])
        self.assertEqual(cart["total_paise"], 14000)

        checkout = connector.create_checkout(cart["cart_id"])
        self.assertIn("chk_acme_", checkout["checkout_id"])

        truth = ProductTruthEngine.evaluate_product(
            {
                "product_id": "prod_tea_01",
                "name": "Earl Grey Tea",
                "source_url": "https://cafeacme.local/p/tea.html",
                "amount_paise": 14000,
            }
        )

        order = connector.create_order(
            request_id="req_99",
            buyer_id="buyer_101",
            product=truth.product,
            payment_transaction_id="txn_pay_101",
            order_binding_hash="hash_bind_101",
        )

        self.assertIn("m_ord_acme_", order["merchant_order_id"])
        self.assertEqual(order["order_status"], "ORDER_CONFIRMED")

        # Verify order lookup
        retrieved = connector.retrieve_order(order["merchant_order_id"])
        self.assertIsNotNone(retrieved)
        assert retrieved is not None
        self.assertEqual(retrieved["payment_transaction_id"], "txn_pay_101")
