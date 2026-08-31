"""
Mandate Gateway — Bounded Cart Combination Optimizer (M28)
Workstream 5 — Generates and optimizes multi-item cart combinations.
Enforces budget bounds, quantity constraints, merchant count limits, and deterministic search.
"""

from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apps.api.commerce.canonical_product import CanonicalProduct
from apps.api.commerce.cart_cost_engine import CartCostEngine, CartCostSummary
from apps.api.commerce.cart_intent import CartOptimizationStrategy, ShoppingRequest
from apps.api.commerce.cart_research import CartResearchResult
from apps.api.commerce.models import CheckoutCapability


@dataclass
class CartCandidate:
    """Evaluated multi-item cart candidate combination."""

    cart_id: str
    items: List[CanonicalProduct]
    quantities: List[int]
    merchant_domains: List[str]
    merchant_count: int
    cost_summary: CartCostSummary
    checkout_capability: CheckoutCapability
    score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cart_id": self.cart_id,
            "items": [item.to_dict() for item in self.items],
            "quantities": self.quantities,
            "merchant_domains": self.merchant_domains,
            "merchant_count": self.merchant_count,
            "cost_summary": self.cost_summary.to_dict(),
            "checkout_capability": self.checkout_capability.value,
            "score": round(self.score, 2),
        }


@dataclass
class CartOptimizationResult:
    """Structured result of multi-item cart optimization."""

    request_id: str
    optimization_strategy: str
    candidates_evaluated: int
    feasible_carts: List[CartCandidate]
    best_recommended_cart: Optional[CartCandidate]
    generated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "optimization_strategy": self.optimization_strategy,
            "candidates_evaluated": self.candidates_evaluated,
            "feasible_carts": [c.to_dict() for c in self.feasible_carts],
            "best_recommended_cart": (
                self.best_recommended_cart.to_dict() if self.best_recommended_cart else None
            ),
            "generated_at": self.generated_at,
        }


class CartOptimizer:
    """
    Deterministic Cart Combination Optimizer.
    Evaluates multi-item cart combinations using bounded search under budget constraints.
    """

    def optimize_cart(
        self, request: ShoppingRequest, research_result: CartResearchResult
    ) -> CartOptimizationResult:
        """Generate feasible cart combinations and rank by optimization strategy."""
        queries = [intent.normalized_query for intent in request.items]
        candidate_lists = [research_result.item_candidates.get(q, []) for q in queries]

        # Check if all items have candidate options
        if not candidate_lists or any(len(lst) == 0 for lst in candidate_lists):
            now_iso = datetime.now(timezone.utc).isoformat()
            return CartOptimizationResult(
                request_id=request.request_id,
                optimization_strategy=request.optimization_strategy.value,
                candidates_evaluated=0,
                feasible_carts=[],
                best_recommended_cart=None,
                generated_at=now_iso,
            )

        quantities = [intent.quantity for intent in request.items]
        evaluated_count = 0
        feasible_carts: List[CartCandidate] = []

        # Cartesian product across candidate lists (bounded top 5 per item to avoid explosion)
        pruned_lists = [lst[:5] for lst in candidate_lists]

        for combination in itertools.product(*pruned_lists):
            evaluated_count += 1
            combo_items = list(combination)

            # Calculate cost
            cost_sum = CartCostEngine.calculate_cart_cost(combo_items, quantities)

            # Constraint 1: Total known cost <= budget
            if cost_sum.total_known_cost_paise > request.total_budget_paise:
                continue

            # Constraint 2: Merchant count limit
            merchant_domains = list({item.merchant_domain for item in combo_items})
            if len(merchant_domains) > request.max_merchant_count:
                continue

            # Evaluate composite checkout capability (lowest capability among items)
            capabilities = [item.checkout_capability for item in combo_items]
            if any(c == CheckoutCapability.DISCOVERY_ONLY for c in capabilities):
                comp_capability = CheckoutCapability.DISCOVERY_ONLY
            elif any(c == CheckoutCapability.CHECKOUT_HANDOFF for c in capabilities):
                comp_capability = CheckoutCapability.CHECKOUT_HANDOFF
            else:
                comp_capability = CheckoutCapability.VERIFIED_API

            # Score cart candidate
            score = self._score_cart(
                combo_items, quantities, cost_sum, len(merchant_domains), comp_capability, request
            )

            cart_id = f"cart_{uuid.uuid4().hex[:10]}"
            candidate = CartCandidate(
                cart_id=cart_id,
                items=combo_items,
                quantities=quantities,
                merchant_domains=merchant_domains,
                merchant_count=len(merchant_domains),
                cost_summary=cost_sum,
                checkout_capability=comp_capability,
                score=score,
            )
            feasible_carts.append(candidate)

        # Sort descending by score
        feasible_carts.sort(key=lambda c: c.score, reverse=True)
        best = feasible_carts[0] if feasible_carts else None
        now_iso = datetime.now(timezone.utc).isoformat()

        return CartOptimizationResult(
            request_id=request.request_id,
            optimization_strategy=request.optimization_strategy.value,
            candidates_evaluated=evaluated_count,
            feasible_carts=feasible_carts,
            best_recommended_cart=best,
            generated_at=now_iso,
        )

    def _score_cart(
        self,
        items: List[CanonicalProduct],
        quantities: List[int],
        cost_sum: CartCostSummary,
        merchant_count: int,
        capability: CheckoutCapability,
        request: ShoppingRequest,
    ) -> float:
        """Calculate weighted score for multi-item cart candidate."""
        # 1. Budget Efficiency (25%)
        budget_used_ratio = cost_sum.total_known_cost_paise / float(request.total_budget_paise)
        budget_score = 25.0 * (1.0 - budget_used_ratio * 0.3)

        # 2. Product Verification Quality (20%)
        ver_count = sum(1 for item in items if item.verification_status == "PRODUCT_VERIFIED")
        verification_score = (ver_count / float(len(items))) * 20.0

        # 3. Merchant Count Efficiency (20%)
        # Single merchant gets top score
        merchant_score = 20.0 / float(merchant_count)

        # 4. Availability Confidence (15%)
        avail_count = sum(1 for item in items if item.availability == "AVAILABLE")
        availability_score = (avail_count / float(len(items))) * 15.0

        # 5. Checkout Capability (10%)
        if capability == CheckoutCapability.VERIFIED_API:
            cap_score = 10.0
        elif capability == CheckoutCapability.CHECKOUT_HANDOFF:
            cap_score = 7.0
        else:
            cap_score = 3.0

        # 6. Freshness (10%)
        freshness_score = 10.0

        # Strategy Adjustments
        strategy = request.optimization_strategy
        if strategy == CartOptimizationStrategy.LOWEST_TOTAL_PRICE:
            # Heavily weight lower price
            budget_score *= 1.5
        elif strategy == CartOptimizationStrategy.FEWEST_MERCHANTS:
            # Heavily weight single merchant
            merchant_score *= 1.5

        return (
            budget_score
            + verification_score
            + merchant_score
            + availability_score
            + cap_score
            + freshness_score
        )
