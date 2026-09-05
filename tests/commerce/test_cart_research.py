"""
Unit tests for Cart Research Engine (M28).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.cart_intent import MultiItemIntentExtractor
from apps.api.commerce.cart_research import CartResearchEngine


class TestCartResearch(unittest.TestCase):
    """CartResearchEngine test suite."""

    def test_01_research_shopping_request(self) -> None:
        """Verify parallel research across multi-item intents."""
        from unittest.mock import patch
        from apps.api.commerce.canonical_product import CanonicalProduct, CheckoutCapability
        from apps.api.commerce.multi_source_discovery import MultiSourceDiscoveryEngine

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

        engine = CartResearchEngine()
        req = MultiItemIntentExtractor.parse_prompt("Find coffee and biscuits under ₹300")

        with patch.object(
            MultiSourceDiscoveryEngine,
            "discover_candidates",
            return_value=([mock_candidate], "SUCCESS"),
        ):
            res = engine.research_shopping_request(req)

        self.assertEqual(res.request_id, req.request_id)
        self.assertIn("coffee", res.item_candidates)
        self.assertGreaterEqual(res.total_candidates_count, 1)
