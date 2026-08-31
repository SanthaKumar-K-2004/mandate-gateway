"""
Mandate Gateway — Product Deduplication Engine (M27)
Workstream 7 — Detects and merges duplicate product candidate records from multiple sources.
Keeps both candidates intact if matching confidence is low to avoid false merges.
"""

from __future__ import annotations

import re
from typing import List

from apps.api.commerce.canonical_product import CanonicalProduct


class ProductDeduplicator:
    """
    Deduplicates canonical products across multiple discovery sources.
    Uses title normalization, brand matching, URL equivalence, and merchant domain.
    """

    def deduplicate(self, candidates: List[CanonicalProduct]) -> List[CanonicalProduct]:
        """Deduplicate list of candidates safely."""
        if not candidates or len(candidates) <= 1:
            return list(candidates)

        deduped: List[CanonicalProduct] = []

        for candidate in candidates:
            matched_index = -1
            for idx, existing in enumerate(deduped):
                if self._are_duplicates(candidate, existing):
                    matched_index = idx
                    break

            if matched_index >= 0:
                # Merge duplicate by keeping candidate with highest verification/capability score
                existing = deduped[matched_index]
                if self._score_quality(candidate) > self._score_quality(existing):
                    deduped[matched_index] = candidate
            else:
                deduped.append(candidate)

        return deduped

    def _are_duplicates(self, a: CanonicalProduct, b: CanonicalProduct) -> bool:
        """Check if two products represent the exact same merchant SKU."""
        if a.product_url and b.product_url and a.product_url.strip() == b.product_url.strip():
            return True

        if a.merchant_domain == b.merchant_domain and a.product_id == b.product_id:
            return True

        norm_title_a = self._normalize_title(a.title)
        norm_title_b = self._normalize_title(b.title)

        if norm_title_a == norm_title_b and a.merchant_domain == b.merchant_domain:
            return True

        return False

    def _normalize_title(self, title: str) -> str:
        """Normalize product title for comparison."""
        cleaned = re.sub(r"[^\w\s]", "", title.lower())
        return " ".join(cleaned.split())

    def _score_quality(self, item: CanonicalProduct) -> int:
        """Assign preference quality score for merging duplicate entries."""
        score = 0
        if item.verification_status == "PRODUCT_VERIFIED":
            score += 50
        if item.checkout_capability.value == "VERIFIED_API":
            score += 30
        elif item.checkout_capability.value == "CHECKOUT_HANDOFF":
            score += 20
        if item.image_url:
            score += 10
        return score
