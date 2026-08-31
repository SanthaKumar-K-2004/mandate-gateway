#!/usr/bin/env python3
"""
Mandate Gateway — Live Multi-Item Cart Research Pilot (M28)
Workstream 13 — Executes end-to-end multi-item live shopping research for:
"Find coffee and biscuits under ₹300"
"""

from __future__ import annotations

import sys

from apps.api.commerce.cart_intent import MultiItemIntentExtractor
from apps.api.commerce.cart_optimizer import CartOptimizer
from apps.api.commerce.cart_research import CartResearchEngine
from apps.api.commerce.recommendation_engine import DeterministicRecommendationEngine


def run_live_cart_research_pilot() -> int:
    """Execute live multi-item cart research pilot."""
    user_prompt = "Find coffee and biscuits under ₹300"
    print("============================================================")
    print(" Mandate Gateway — Autonomous Multi-Item Cart Research Pilot")
    print(f" Request: '{user_prompt}'")
    print("============================================================")

    # 1. Intent Extraction
    print("\n[Stage 1/5] Multi-Item Intent Extraction...")
    shop_req = MultiItemIntentExtractor.parse_prompt(user_prompt, default_budget_paise=30000)
    print(f" -> Total Budget Limit: ₹{shop_req.total_budget_paise/100:.2f} INR")
    print(f" -> Strategy: {shop_req.optimization_strategy.value}")
    for item in shop_req.items:
        print(f"    • Requested Item: '{item.item_name}' (Quantity: {item.quantity})")

    # 2. Parallel Live Product Research
    print("\n[Stage 2/5] Parallel Live Product Research...")
    research_engine = CartResearchEngine()
    research_res = research_engine.research_shopping_request(shop_req)
    print(f" -> Researched Candidates Count: {research_res.total_candidates_count}")
    for item_query, candidates in research_res.item_candidates.items():
        print(f"    • Item '{item_query}': {len(candidates)} verified candidates found")

    # 3. Bounded Cart Optimization
    print("\n[Stage 3/5] Bounded Cart Combination Optimization...")
    optimizer = CartOptimizer()
    opt_res = optimizer.optimize_cart(shop_req, research_res)
    print(f" -> Candidates Evaluated: {opt_res.candidates_evaluated}")
    print(f" -> Feasible Cart Combinations: {len(opt_res.feasible_carts)}")

    best_cart = opt_res.best_recommended_cart
    assert best_cart is not None, "No feasible verified cart combination found!"

    # 4. Total Cost Truth Calculation
    print("\n[Stage 4/5] Total Cost Truth & Unknown Fee Detection...")
    cost = best_cart.cost_summary
    print(f" -> Verified Product Subtotal: ₹{cost.product_subtotal_paise/100:.2f} INR")
    print(f" -> Known Total Cost: ₹{cost.total_known_cost_paise/100:.2f} INR")
    if cost.unknown_cost_components:
        print(f" -> Unknown Fee Components: {', '.join(cost.unknown_cost_components)}")
        print(" [!] NOTICE: Delivery and tax costs are unverified (UNKNOWN) from live sources.")

    # 5. Recommendation Explainability
    print("\n[Stage 5/5] Cart Recommendation Explainability...")
    rec_engine = DeterministicRecommendationEngine()
    explanation = rec_engine.explain_cart_recommendation(best_cart, shop_req.total_budget_paise)
    print(f" -> Cart Recommendation Score: {best_cart.score:.1f} / 100")
    print(" -> Why Recommended:")
    for point in explanation:
        print(f"    • {point}")

    print("\n============================================================")
    print(" [✓] AUTONOMOUS MULTI-ITEM CART RESEARCH PILOT COMPLETED CLEANLY!")
    print("============================================================")
    return 0


if __name__ == "__main__":
    sys.exit(run_live_cart_research_pilot())
