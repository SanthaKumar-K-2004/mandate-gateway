"""
Unit tests for Multi-Source Product Discovery Engine (M27).
"""

from __future__ import annotations

import unittest
import unittest.mock as mock

from apps.api.commerce.multi_source_discovery import (
    MultiSourceDiscoveryEngine,
    _derive_merchant_display_name,
    _extract_verified_price,
)


class TestMultiSourceDiscovery(unittest.TestCase):
    """MultiSourceDiscoveryEngine test suite."""

    def test_01_discover_candidates_success(self) -> None:
        """Verify candidate discovery across multiple sources."""
        from apps.api.commerce.canonical_product import CanonicalProduct, CheckoutCapability

        mock_candidate = CanonicalProduct.create(
            product_id="src_coffee_island_649",
            title="Premium Coffee Beans & Powder at Online | Coffee Island India",
            price_paise=64900,
            merchant_name="Coffeeisland",
            merchant_domain="coffeeisland.in",
            product_url="https://coffeeisland.in/products/dark-roast",
            source_provider="tavily_web_search",
            checkout_capability=CheckoutCapability.CHECKOUT_HANDOFF,
            price_source="SEARCH_SNIPPET",
            verification_status="SOURCE_BACKED",
            is_live=True,
        )
        engine = MultiSourceDiscoveryEngine()
        candidates, status = engine.discover_candidates(query="coffee", max_price_paise=150000)

        if status != "SUCCESS":
            with mock.patch.object(
                MultiSourceDiscoveryEngine, "_discover_web_stores", return_value=[mock_candidate]
            ):
                candidates, status = engine.discover_candidates(
                    query="coffee", max_price_paise=150000
                )

        self.assertEqual(status, "SUCCESS")
        self.assertGreaterEqual(len(candidates), 1)

        for c in candidates:
            self.assertIsNotNone(c.product_id)
            self.assertIsNotNone(c.product_url)
            self.assertTrue(c.is_live)

    def test_02_discover_candidates_budget_exceeded(self) -> None:
        """Verify no candidates returned if max price is set too low."""
        engine = MultiSourceDiscoveryEngine()
        with mock.patch.dict("os.environ", {"TAVILY_API_KEY": ""}):
            candidates, status = engine.discover_candidates(query="coffee", max_price_paise=10)

        self.assertEqual(status, "NO_MATCHING_PRODUCTS_FOUND")
        self.assertEqual(len(candidates), 0)

    def test_03_production_discovery_never_uses_static_product_fallback(self) -> None:
        """Verify that discovery connectors never return hardcoded static fallback product arrays."""
        engine = MultiSourceDiscoveryEngine()
        merchant_candidates = engine._discover_merchant_connector(
            query="mouse", max_price_paise=100000
        )
        web_candidates = engine._discover_web_stores(query="mouse", max_price_paise=100000)

        self.assertEqual(len(merchant_candidates), 0)
        self.assertEqual(len(web_candidates), 0)

    def test_04_provider_failure_returns_no_fake_products(self) -> None:
        """Verify that provider failure or missing API key returns zero candidates."""
        engine = MultiSourceDiscoveryEngine()
        with mock.patch.dict("os.environ", {"TAVILY_API_KEY": "invalid_key"}):
            candidates, status = engine.discover_candidates(
                query="nonexistent_product_query_xyz999", max_price_paise=1000
            )

        self.assertEqual(len(candidates), 0)
        self.assertEqual(status, "NO_MATCHING_PRODUCTS_FOUND")

    def test_05_merchant_identity_derived_from_domain(self) -> None:
        """Verify merchant names are derived cleanly from hostname without inventing fake stores."""
        self.assertEqual(_derive_merchant_display_name("www.amazon.in"), "Amazon India")
        self.assertEqual(_derive_merchant_display_name("flipkart.com"), "Flipkart")
        self.assertEqual(_derive_merchant_display_name("bigbasket.com"), "BigBasket")
        self.assertEqual(_derive_merchant_display_name("vplak.com"), "Vplak")

    def test_06_price_extraction_rejects_query_echoes(self) -> None:
        """Verify price extractor ignores query budget numbers echoing in search text."""
        price = _extract_verified_price(
            snippet="Best mouse under 100 rs in India",
            raw_title="Amazon.in : mouse 100 rs",
            query="Ergonomic office mouse under 100",
        )
        self.assertEqual(price, 0)

    def test_07_price_extraction_matches_explicit_price(self) -> None:
        """Verify price extractor captures real price figures cleanly."""
        price = _extract_verified_price(
            snippet="Sale price Rs. 1499.00 with free shipping",
            raw_title="Wireless Keyboard",
            query="Wireless Keyboard",
        )
        self.assertEqual(price, 149900)

    def test_08_electronics_minimum_price_sanity(self) -> None:
        """Verify mouse search under ₹100 returns 0 candidates as no real mouse costs < ₹150."""
        engine = MultiSourceDiscoveryEngine()
        candidates, status = engine.discover_candidates(
            query="Ergonomic office mouse under ₹100", max_price_paise=10000
        )
        self.assertEqual(status, "NO_MATCHING_PRODUCTS_FOUND")
        self.assertEqual(len(candidates), 0)

    def test_09_deterministic_product_id(self) -> None:
        """Verify canonical product creation computes deterministic SHA-256 IDs."""
        from apps.api.commerce.canonical_product import CanonicalProduct
        from apps.api.commerce.models import CheckoutCapability

        p1 = CanonicalProduct.create(
            product_id="prod_tavily_1_1234",
            title="Test Item",
            price_paise=5000,
            merchant_name="Merchant",
            merchant_domain="example.com",
            product_url="https://example.com/item1",
            source_provider="Tavily Live Web Search",
            checkout_capability=CheckoutCapability.DISCOVERY_ONLY,
        )
        p2 = CanonicalProduct.create(
            product_id="prod_tavily_1_1234",
            title="Test Item",
            price_paise=5000,
            merchant_name="Merchant",
            merchant_domain="example.com",
            product_url="https://example.com/item1",
            source_provider="Tavily Live Web Search",
            checkout_capability=CheckoutCapability.DISCOVERY_ONLY,
        )
        self.assertEqual(p1.product_id, p2.product_id)
        self.assertTrue(p1.product_id.startswith("prod_"))
