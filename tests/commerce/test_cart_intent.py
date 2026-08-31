"""
Unit tests for Multi-Item Intent Extraction (M28).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.cart_intent import (
    CartOptimizationStrategy,
    MultiItemIntentExtractor,
)


class TestCartIntent(unittest.TestCase):
    """MultiItemIntentExtractor test suite."""

    def test_01_parse_multi_item_prompt(self) -> None:
        """Verify parsing prompt into multi-item ShoppingRequest."""
        prompt = "Find coffee and biscuits under ₹300"
        req = MultiItemIntentExtractor.parse_prompt(prompt, default_budget_paise=50000)

        self.assertEqual(req.total_budget_paise, 30000)
        self.assertEqual(len(req.items), 2)
        self.assertEqual(req.items[0].normalized_query, "coffee")
        self.assertEqual(req.items[1].normalized_query, "biscuits")
        self.assertEqual(req.optimization_strategy, CartOptimizationStrategy.BEST_VALUE)

    def test_02_parse_cheapest_strategy(self) -> None:
        """Verify parsing cheapest optimization strategy preference."""
        prompt = "Find cheapest coffee, biscuits and milk under ₹500"
        req = MultiItemIntentExtractor.parse_prompt(prompt)

        self.assertEqual(req.total_budget_paise, 50000)
        self.assertEqual(len(req.items), 3)
        self.assertEqual(req.optimization_strategy, CartOptimizationStrategy.LOWEST_TOTAL_PRICE)
