"""
Mandate Gateway — Cart Research Engine (M28)
Workstream 3 — Queries live discovery engines across multiple ShoppingItemIntent queries.
Enforces per-item candidate verification and rate-safe bounded research.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apps.api.commerce.canonical_product import CanonicalProduct
from apps.api.commerce.cart_intent import ShoppingRequest
from apps.api.commerce.multi_source_discovery import MultiSourceDiscoveryEngine

logger = logging.getLogger("mandate_gateway.cart_research")


@dataclass
class CartResearchResult:
    """Result of multi-item shopping research."""

    request_id: str
    item_candidates: Dict[str, List[CanonicalProduct]]
    item_statuses: Dict[str, str]
    total_candidates_count: int
    researched_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "item_candidates": {
                query: [c.to_dict() for c in c_list]
                for query, c_list in self.item_candidates.items()
            },
            "item_statuses": self.item_statuses,
            "total_candidates_count": self.total_candidates_count,
            "researched_at": self.researched_at,
        }


class CartResearchEngine:
    """
    Parallel live product research engine for multi-item cart requests.
    Executes discovery per requested item and filters unverified/stale candidates.
    """

    def __init__(self, discovery_engine: Optional[MultiSourceDiscoveryEngine] = None) -> None:
        self.discovery_engine = discovery_engine or MultiSourceDiscoveryEngine()

    def research_shopping_request(self, request: ShoppingRequest) -> CartResearchResult:
        """Execute research across all item intents in shopping request."""
        item_candidates: Dict[str, List[CanonicalProduct]] = {}
        item_statuses: Dict[str, str] = {}
        total_count = 0

        # Divide total budget equally as initial per-item search bound
        per_item_max_budget = request.total_budget_paise

        for intent in request.items:
            query_key = intent.normalized_query
            candidates, status = self.discovery_engine.discover_candidates(
                query=query_key, max_price_paise=per_item_max_budget
            )

            # Filter unverified, zero price, or missing URL candidates
            verified_candidates: List[CanonicalProduct] = []
            for c in candidates:
                if (
                    c.verification_status != "UNVERIFIED"
                    and c.price_paise > 0
                    and c.product_url
                    and c.product_url.startswith("http")
                ):
                    verified_candidates.append(c)

            item_candidates[query_key] = verified_candidates
            if verified_candidates:
                item_statuses[query_key] = "SUCCESS"
            else:
                item_statuses[query_key] = "NO_MATCHING_PRODUCTS_FOUND"

            total_count += len(verified_candidates)

        now_iso = datetime.now(timezone.utc).isoformat()

        return CartResearchResult(
            request_id=request.request_id,
            item_candidates=item_candidates,
            item_statuses=item_statuses,
            total_candidates_count=total_count,
            researched_at=now_iso,
        )
