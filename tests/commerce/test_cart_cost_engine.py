"""
Unit tests for Total Cost Truth Engine (M28).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.canonical_product import CanonicalProduct
from apps.api.commerce.cart_cost_engine import CartCostEngine
from apps.api.commerce.models import CheckoutCapability


class TestCartCostEngine(unittest.TestCase):
    """CartCostEngine test suite."""

    def test_01_calculate_cart_cost_with_unknowns(self) -> None:
        """Verify unverified shipping and tax are marked UNKNOWN."""
        p1 = CanonicalProduct.create(
            product_id="prod_01",
            title="Coffee",
            price_paise=18000,
            merchant_name="Merchant A",
            merchant_domain="shop.com",
            product_url="https://shop.com/1",
            source_provider="Provider A",
            checkout_capability=CheckoutCapability.VERIFIED_API,
        )

        cost = CartCostEngine.calculate_cart_cost([p1], quantities=[1])

        self.assertEqual(cost.product_subtotal_paise, 18000)
        self.assertIn("SHIPPING_COST", cost.unknown_cost_components)
        self.assertIn("MERCHANT_TAX", cost.unknown_cost_components)
        self.assertFalse(cost.is_total_fully_verified)
