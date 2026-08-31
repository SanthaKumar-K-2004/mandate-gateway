"""
Unit tests for Public Platform Commerce Connector (M26).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.connectors.public_platform import PublicPlatformConnector
from apps.api.commerce.models import CheckoutCapability
from apps.api.commerce.product_truth_engine import ProductTruthEngine


class TestPublicPlatformConnector(unittest.TestCase):
    """PublicPlatformConnector test suite."""

    def test_01_supports_domain(self) -> None:
        """Verify supported domain matching for public catalog."""
        connector = PublicPlatformConnector()
        self.assertTrue(connector.supports_domain("world.openfoodfacts.org"))
        self.assertTrue(connector.supports_domain("api.openfoodfacts.org"))
        self.assertFalse(connector.supports_domain("unknown.com"))

    def test_02_capability_declaration(self) -> None:
        """Verify capability is declared as VERIFIED_API."""
        connector = PublicPlatformConnector()
        self.assertEqual(connector.capability, CheckoutCapability.VERIFIED_API)

    def test_03_create_order_and_verify(self) -> None:
        """Verify public catalog direct API cart, checkout, and order creation flow."""
        connector = PublicPlatformConnector()

        truth = ProductTruthEngine.evaluate_product(
            {
                "product_id": "prod_off_espresso_250",
                "name": "Espresso Roast Coffee Beans 250g",
                "source_url": "https://world.openfoodfacts.org/product/espresso.html",
                "amount_paise": 18000,
            }
        )

        order = connector.create_order(
            request_id="req_off_101",
            buyer_id="buyer_off_101",
            product=truth.product,
            payment_transaction_id="txn_pay_off_101",
            order_binding_hash="hash_bind_off_101",
        )

        self.assertIn("m_ord_off_", order["merchant_order_id"])
        self.assertEqual(order["order_status"], "ORDER_CONFIRMED")

        # Verify order lookup
        retrieved = connector.retrieve_order(order["merchant_order_id"])
        self.assertIsNotNone(retrieved)
        assert retrieved is not None
        self.assertEqual(retrieved["payment_transaction_id"], "txn_pay_off_101")
