"""
Unit tests for Cart Combination Optimizer (M28).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.cart_intent import MultiItemIntentExtractor
from apps.api.commerce.cart_optimizer import CartOptimizer
from apps.api.commerce.cart_research import CartResearchEngine


class TestCartOptimizer(unittest.TestCase):
    """CartOptimizer test suite."""

    def test_01_optimize_cart_success(self) -> None:
        """Verify cart combination evaluation under total budget bounds."""
        req = MultiItemIntentExtractor.parse_prompt("Find coffee and biscuits under ₹400")
        research_eng = CartResearchEngine()
        research_res = research_eng.research_shopping_request(req)

        optimizer = CartOptimizer()
        opt_res = optimizer.optimize_cart(req, research_res)

        self.assertEqual(opt_res.request_id, req.request_id)
        if opt_res.best_recommended_cart:
            best = opt_res.best_recommended_cart
            self.assertLessEqual(best.cost_summary.total_known_cost_paise, 40000)
            self.assertGreaterEqual(len(best.items), 1)
