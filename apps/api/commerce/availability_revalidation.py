"""
Mandate Gateway — Live Availability Revalidation Engine (M24)
Workstream 4 — Revalidates product availability prior to checkout preparation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from apps.api.commerce.models import AvailabilityEvidence, VerifiedProduct


class LiveAvailabilityRevalidator:
    """Live Availability Revalidation Engine."""

    @classmethod
    def revalidate(
        cls,
        product: VerifiedProduct,
        current_live_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, AvailabilityEvidence]:
        """
        Revalidate original verified product availability against current live stock status.
        Returns: (is_available: bool, availability_evidence: AvailabilityEvidence)
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        is_in_stock = product.availability.is_in_stock
        stock_qty = product.availability.stock_quantity
        evidence_url = product.source_url

        if current_live_data:
            if "availability" in current_live_data:
                is_in_stock = bool(current_live_data["availability"])
            if "stock_quantity" in current_live_data:
                stock_qty = current_live_data["stock_quantity"]
            if "source_url" in current_live_data:
                evidence_url = current_live_data["source_url"]

        ev = AvailabilityEvidence(
            is_in_stock=is_in_stock,
            stock_quantity=stock_qty,
            verified_at=now_iso,
            evidence_url=evidence_url,
        )

        return is_in_stock, ev
