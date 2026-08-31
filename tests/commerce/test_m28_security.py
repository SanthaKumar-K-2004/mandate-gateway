"""
Unit tests for Milestone M28 Security & Adversarial Threat Model Rules.
"""

from __future__ import annotations

import unittest

from apps.api.commerce.canonical_product import CanonicalProduct
from apps.api.commerce.cart_cost_engine import CartCostEngine
from apps.api.commerce.cart_intent import MultiItemIntentExtractor
from apps.api.commerce.cart_optimizer import CartOptimizer
from apps.api.commerce.cart_research import CartResearchResult
from apps.api.commerce.models import CheckoutCapability


class TestM28Security(unittest.TestCase):
    """M28 Security & Adversarial Threat Model test suite."""

    def test_01_budget_overrun_rejected(self) -> None:
        """Verify cart combinations exceeding prompt total budget are rejected."""
        req = MultiItemIntentExtractor.parse_prompt("Find coffee under ₹100")
        p1 = CanonicalProduct.create(
            product_id="prod_expensive_01",
            title="Expensive Coffee",
            price_paise=18000,  # ₹180 exceeds ₹100 budget
            merchant_name="Merchant A",
            merchant_domain="shop.com",
            product_url="https://shop.com/exp",
            source_provider="Provider A",
            checkout_capability=CheckoutCapability.VERIFIED_API,
        )
        research_res = CartResearchResult(
            request_id=req.request_id,
            item_candidates={"coffee": [p1]},
            item_statuses={"coffee": "SUCCESS"},
            total_candidates_count=1,
            researched_at="2026-08-31T00:00:00Z",
        )

        optimizer = CartOptimizer()
        opt_res = optimizer.optimize_cart(req, research_res)

        self.assertIsNone(opt_res.best_recommended_cart)
        self.assertEqual(len(opt_res.feasible_carts), 0)

    def test_02_unknown_shipping_cost_unestimated(self) -> None:
        """Verify unknown shipping costs are strictly marked UNKNOWN and not estimated."""
        p1 = CanonicalProduct.create(
            product_id="prod_01",
            title="Coffee",
            price_paise=15000,
            merchant_name="Merchant A",
            merchant_domain="shop.com",
            product_url="https://shop.com/1",
            source_provider="Provider A",
            checkout_capability=CheckoutCapability.VERIFIED_API,
        )

        cost = CartCostEngine.calculate_cart_cost([p1], quantities=[1])
        self.assertIn("SHIPPING_COST", cost.unknown_cost_components)
        self.assertIsNone(cost.shipping_cost_paise)
