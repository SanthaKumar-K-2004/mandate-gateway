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
        engine = CartResearchEngine()
        req = MultiItemIntentExtractor.parse_prompt("Find coffee and biscuits under ₹300")
        res = engine.research_shopping_request(req)

        self.assertEqual(res.request_id, req.request_id)
        self.assertIn("coffee", res.item_candidates)
        self.assertGreaterEqual(res.total_candidates_count, 1)
