"""
Unit tests for Product Comparison Engine (M27).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.canonical_product import CanonicalProduct
from apps.api.commerce.models import CheckoutCapability
from apps.api.commerce.product_comparison import ProductComparisonEngine


class TestProductComparison(unittest.TestCase):
    """ProductComparisonEngine test suite."""

    def test_01_compare_candidates(self) -> None:
        """Verify evidence factor evaluation across candidates."""
        engine = ProductComparisonEngine()

        c1 = CanonicalProduct.create(
            product_id="prod_off_coffee_250",
            title="Espresso Roast Coffee Beans 250g",
            price_paise=18000,
            merchant_name="OpenFoodFacts Public Catalog",
            merchant_domain="world.openfoodfacts.org",
            product_url="https://world.openfoodfacts.org/product/2000000000018",
            source_provider="OpenFoodFacts API",
            checkout_capability=CheckoutCapability.VERIFIED_API,
        )
        c2 = CanonicalProduct.create(
            product_id="prod_cafe_acme_01",
            title="Acme Artisan Espresso Coffee 250g",
            price_paise=19000,
            merchant_name="Cafe Acme Direct",
            merchant_domain="cafeacme.local",
            product_url="http://cafeacme.local/menu/espresso",
            source_provider="Cafe Acme Merchant API",
            checkout_capability=CheckoutCapability.VERIFIED_API,
        )

        res = engine.compare_candidates(
            query="coffee",
            max_price_paise=20000,
            candidates=[c1, c2],
            recommended_id="prod_off_coffee_250",
        )

        self.assertEqual(res.candidates_count, 2)
        self.assertEqual(res.recommended_candidate_id, "prod_off_coffee_250")
        self.assertEqual(len(res.factors), 2)
        self.assertTrue(res.factors[0].budget_fit)
