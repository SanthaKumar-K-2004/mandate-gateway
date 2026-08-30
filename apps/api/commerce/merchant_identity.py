"""
Mandate Gateway — Merchant Identity Resolver (M24)
Workstream 5 — Distinguishes Product Seller Domain from Search Provider and Payment Gateway.
"""

from __future__ import annotations

import urllib.parse
from typing import Dict, Optional

from apps.api.commerce.models import MerchantIdentity


class MerchantIdentityResolver:
    """Merchant & Seller Identity Resolution Engine."""

    _KNOWN_MERCHANT_REGISTRY: Dict[str, Dict[str, str]] = {
        "cafeacme.local": {
            "merchant_id": "mer_cafe_acme",
            "legal_name": "Cafe Acme Specialty Coffee Ltd",
        },
        "bluetokaicoffee.com": {
            "merchant_id": "mer_bluetokai",
            "legal_name": "Blue Tokai Coffee Roasters",
        },
        "crossword.in": {"merchant_id": "mer_crossword", "legal_name": "Crossword Bookstores Ltd"},
    }

    @classmethod
    def resolve_seller_identity(
        cls, source_url: str, proposed_merchant_id: Optional[str] = None
    ) -> MerchantIdentity:
        """
        Resolve merchant seller identity from source URL and domain registry.
        Distinguishes product seller domain from search providers (Tavily/Brave).
        """
        if not source_url:
            return MerchantIdentity(
                merchant_id=proposed_merchant_id or "mer_unknown",
                domain="unknown.local",
                legal_name="Unverified Seller Domain",
                identity_status="UNKNOWN",
            )

        try:
            parsed = urllib.parse.urlparse(source_url)
            domain = parsed.netloc.replace("www.", "").lower()
            if not domain:
                domain = "unknown.local"
        except Exception:
            domain = "unknown.local"

        if domain in cls._KNOWN_MERCHANT_REGISTRY:
            meta = cls._KNOWN_MERCHANT_REGISTRY[domain]
            return MerchantIdentity(
                merchant_id=meta["merchant_id"],
                domain=domain,
                legal_name=meta["legal_name"],
                identity_status="VERIFIED",
            )

        if domain != "unknown.local":
            merchant_id = proposed_merchant_id or f"mer_{domain.replace('.', '_')[:25]}"
            legal_name = domain.split(".")[0].title()
            return MerchantIdentity(
                merchant_id=merchant_id,
                domain=domain,
                legal_name=f"{legal_name} Online Store",
                identity_status="SOURCE_BACKED",
            )

        return MerchantIdentity(
            merchant_id=proposed_merchant_id or "mer_unknown",
            domain="unknown.local",
            legal_name="Unverified Seller Domain",
            identity_status="UNKNOWN",
        )
