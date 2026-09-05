"""
Mandate Gateway — Canonical Normalized Product Model (M27)
Workstream 4 — Canonical representation of products across multiple real commerce sources.
Every candidate product maintains strict source evidence and provenance.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from apps.api.commerce.models import CheckoutCapability


@dataclass
class CanonicalProduct:
    """Canonical evidence-backed normalized product candidate."""

    product_id: str
    title: str
    brand: str
    description: str
    category: str
    price_paise: int
    currency: str
    availability: str  # IN_STOCK, OUT_OF_STOCK, UNKNOWN
    merchant_name: str
    merchant_domain: str
    product_url: str
    image_url: Optional[str]
    source_provider: str
    retrieved_at: str
    evidence_hash: str
    verification_status: str  # PRODUCT_VERIFIED, PRICE_UNVERIFIED, UNVERIFIED
    checkout_capability: CheckoutCapability
    price_source: str = "UNKNOWN"  # VERIFIED_MERCHANT, SOURCE_REPORTED, SEARCH_SNIPPET, UNKNOWN
    is_live: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert canonical product to dictionary for JSON serialization."""
        return {
            "product_id": self.product_id,
            "title": self.title,
            "brand": self.brand,
            "description": self.description,
            "category": self.category,
            "price_paise": self.price_paise,
            "price_inr": (
                round(self.price_paise / 100.0, 2) if self.price_paise is not None else None
            ),
            "currency": self.currency,
            "availability": self.availability,
            "merchant_name": self.merchant_name,
            "merchant_domain": self.merchant_domain,
            "product_url": self.product_url,
            "image_url": self.image_url,
            "source_provider": self.source_provider,
            "retrieved_at": self.retrieved_at,
            "evidence_hash": self.evidence_hash,
            "verification_status": self.verification_status,
            "checkout_capability": (
                self.checkout_capability.value
                if isinstance(self.checkout_capability, CheckoutCapability)
                else str(self.checkout_capability)
            ),
            "price_source": self.price_source,
            "is_live": self.is_live,
        }

    @classmethod
    def create(
        cls,
        product_id: str,
        title: str,
        price_paise: int,
        merchant_name: str,
        merchant_domain: str,
        product_url: str,
        source_provider: str,
        checkout_capability: CheckoutCapability,
        brand: str = "UNKNOWN",
        description: str = "",
        category: str = "general",
        currency: str = "INR",
        availability: str = "UNKNOWN",
        image_url: Optional[str] = None,
        verification_status: str = "PRODUCT_VERIFIED",
        price_source: str = "UNKNOWN",
        is_live: bool = True,
    ) -> CanonicalProduct:
        """Factory constructor computing evidence hash deterministically."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # Generate deterministic product ID from SHA-256 if standard prefix passed
        if not product_id or product_id.startswith("prod_tavily_"):
            sha_part = hashlib.sha256(
                f"{source_provider}:{merchant_domain}:{product_url}".encode("utf-8")
            ).hexdigest()[:16]
            product_id = f"prod_{sha_part}"

        raw_evidence = (
            f"{product_id}|{title}|{price_paise}|{merchant_domain}|{product_url}|{source_provider}"
        )
        evidence_hash = hashlib.sha256(raw_evidence.encode("utf-8")).hexdigest()

        return cls(
            product_id=product_id,
            title=title,
            brand=brand or "UNKNOWN",
            description=description or "",
            category=category or "general",
            price_paise=price_paise,
            currency=currency,
            availability=availability or "UNKNOWN",
            merchant_name=merchant_name or merchant_domain,
            merchant_domain=merchant_domain,
            product_url=product_url,
            image_url=image_url if image_url else None,
            source_provider=source_provider,
            retrieved_at=now_iso,
            evidence_hash=evidence_hash,
            verification_status=verification_status,
            checkout_capability=checkout_capability,
            price_source=price_source,
            is_live=is_live,
        )
