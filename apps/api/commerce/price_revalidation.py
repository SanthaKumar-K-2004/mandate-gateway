"""
Mandate Gateway — Live Price Revalidation Engine (M24)
Workstream 3 — Revalidates live price before checkout or payment execution.
Detects price mutations and invalidates existing confirmation tokens if price has changed.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from apps.api.commerce.models import PriceEvidence, VerifiedProduct


class PriceRevalidationError(RuntimeError):
    """Raised when price revalidation fails or detects an unauthorized price change."""

    pass


class LivePriceRevalidator:
    """Live Price Revalidation Engine."""

    @classmethod
    def revalidate(
        cls,
        product: VerifiedProduct,
        current_live_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, PriceEvidence, bool]:
        """
        Revalidate original verified product price against current live data.
        Returns:
            (is_valid: bool, current_price: PriceEvidence, price_changed: bool)
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        original_price_paise = product.price.amount_paise

        current_price_paise = original_price_paise
        evidence_url = product.source_url

        if current_live_data:
            current_price_paise = int(current_live_data.get("amount_paise", original_price_paise))
            evidence_url = current_live_data.get("source_url", product.source_url)

        raw_ev = f"{evidence_url}|{current_price_paise}|{product.price.currency}|{now_iso}"
        ev_hash = hashlib.sha256(raw_ev.encode("utf-8")).hexdigest()

        current_price = PriceEvidence(
            amount_paise=current_price_paise,
            currency=product.price.currency,
            verified_at=now_iso,
            evidence_url=evidence_url,
            evidence_hash=ev_hash,
        )

        price_changed = current_price_paise != original_price_paise

        if price_changed:
            # Price mutation detected -> Fail validation to trigger token invalidation and new human confirmation
            return False, current_price, True

        return True, current_price, False
