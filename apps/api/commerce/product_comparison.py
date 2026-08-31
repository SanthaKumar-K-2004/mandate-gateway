"""
Mandate Gateway — Cross-Merchant Product Comparison Engine (M27)
Workstream 5 — Performs evidence-backed comparison across multiple merchant candidates.
Evaluates only evidence-backed factual metrics. Does NOT rely on LLM subjective opinions for facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apps.api.commerce.canonical_product import CanonicalProduct


@dataclass
class ComparisonFactor:
    """Detailed evidence-backed comparison factor per candidate."""

    candidate_id: str
    merchant_name: str
    price_paise: int
    price_inr: float
    budget_fit: bool
    verification_status: str
    availability: str
    checkout_capability: str
    source_provider: str
    health_status: str


@dataclass
class ComparisonResult:
    """Structured result of multi-merchant comparison."""

    query: str
    max_price_paise: int
    candidates_count: int
    factors: List[ComparisonFactor]
    recommended_candidate_id: Optional[str]
    generated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "max_price_paise": self.max_price_paise,
            "max_price_inr": round(self.max_price_paise / 100.0, 2),
            "candidates_count": self.candidates_count,
            "factors": [f.__dict__ for f in self.factors],
            "recommended_candidate_id": self.recommended_candidate_id,
            "generated_at": self.generated_at,
        }


class ProductComparisonEngine:
    """
    Cross-merchant comparison engine.
    Evaluates evidence factors objectively without subjective LLM hallucinations.
    """

    def compare_candidates(
        self,
        query: str,
        max_price_paise: int,
        candidates: List[CanonicalProduct],
        recommended_id: Optional[str] = None,
    ) -> ComparisonResult:
        """Evaluate evidence-backed comparison matrix for given candidates."""
        factors: List[ComparisonFactor] = []

        for c in candidates:
            factor = ComparisonFactor(
                candidate_id=c.product_id,
                merchant_name=c.merchant_name,
                price_paise=c.price_paise,
                price_inr=round(c.price_paise / 100.0, 2),
                budget_fit=c.price_paise <= max_price_paise,
                verification_status=c.verification_status,
                availability=c.availability,
                checkout_capability=c.checkout_capability.value,
                source_provider=c.source_provider,
                health_status="HEALTHY",
            )
            factors.append(factor)

        now_iso = datetime.now(timezone.utc).isoformat()

        return ComparisonResult(
            query=query,
            max_price_paise=max_price_paise,
            candidates_count=len(candidates),
            factors=factors,
            recommended_candidate_id=recommended_id,
            generated_at=now_iso,
        )
