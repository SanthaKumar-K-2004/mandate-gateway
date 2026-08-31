"""
Unit tests for Deterministic Recommendation Engine & Recommendation Safety (M27).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.canonical_product import CanonicalProduct
from apps.api.commerce.models import CheckoutCapability
from apps.api.commerce.recommendation_engine import DeterministicRecommendationEngine


class TestRecommendationEngine(unittest.TestCase):
    """DeterministicRecommendationEngine test suite."""

    def test_01_rank_candidates_deterministic(self) -> None:
        """Verify deterministic candidate ranking by weighted score."""
        engine = DeterministicRecommendationEngine()

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
            product_id="prod_web_coffee_99",
            title="Filter Coffee Powder 250g",
            price_paise=15000,
            merchant_name="Coffee Roasters India",
            merchant_domain="coffeeroasters.in",
            product_url="https://coffeeroasters.in/products/dark-roast",
            source_provider="Web Discovery Engine",
            checkout_capability=CheckoutCapability.CHECKOUT_HANDOFF,
        )

        best, scored, status = engine.rank_candidates([c1, c2], max_price_paise=20000)

        self.assertEqual(status, "SUCCESS")
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(
            best.product.product_id, "prod_off_coffee_250"
        )  # VERIFIED_API scores higher than HANDOFF
        self.assertGreaterEqual(best.total_score, 80.0)

    def test_02_recommendation_safety_rejects_unverified(self) -> None:
        """Verify recommendation engine safety rule rejects UNVERIFIED products."""
        engine = DeterministicRecommendationEngine()

        unverified = CanonicalProduct.create(
            product_id="prod_fake_01",
            title="Unverified Coffee",
            price_paise=10000,
            merchant_name="Unknown Store",
            merchant_domain="unknown.com",
            product_url="https://unknown.com/fake",
            source_provider="Fake Source",
            checkout_capability=CheckoutCapability.DISCOVERY_ONLY,
            verification_status="UNVERIFIED",
        )

        best, scored, status = engine.rank_candidates([unverified], max_price_paise=20000)
        self.assertIsNone(best)
        self.assertIn("No sufficiently verified products", status)
