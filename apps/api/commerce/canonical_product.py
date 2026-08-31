"""
Mandate Gateway — Canonical Normalized Product Model (M27)
Workstream 4 — Canonical representation of products across multiple real commerce sources.
Every candidate product maintains strict source evidence and provenance.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

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
    availability: str  # AVAILABLE, OUT_OF_STOCK, UNKNOWN
    merchant_name: str
    merchant_domain: str
    product_url: str
    image_url: str
    source_provider: str
    retrieved_at: str
    evidence_hash: str
    verification_status: str  # PRODUCT_VERIFIED, PRICE_UNVERIFIED, UNVERIFIED
    checkout_capability: CheckoutCapability

    def to_dict(self) -> Dict[str, Any]:
        """Convert canonical product to dictionary for JSON serialization."""
        return {
            "product_id": self.product_id,
            "title": self.title,
            "brand": self.brand,
            "description": self.description,
            "category": self.category,
            "price_paise": self.price_paise,
            "price_inr": round(self.price_paise / 100.0, 2),
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
            "checkout_capability": self.checkout_capability.value,
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
        category: str = "coffee",
        currency: str = "INR",
        availability: str = "AVAILABLE",
        image_url: str = "",
        verification_status: str = "PRODUCT_VERIFIED",
    ) -> CanonicalProduct:
        """Factory constructor computing evidence hash deterministically."""
        now_iso = datetime.now(timezone.utc).isoformat()
        raw_evidence = (
            f"{product_id}|{title}|{price_paise}|{merchant_domain}|{product_url}|{source_provider}"
        )
        evidence_hash = hashlib.sha256(raw_evidence.encode("utf-8")).hexdigest()

        return cls(
            product_id=product_id,
            title=title,
            brand=brand or "UNKNOWN",
            description=description or "",
            category=category or "coffee",
            price_paise=price_paise,
            currency=currency,
            availability=availability or "AVAILABLE",
            merchant_name=merchant_name or merchant_domain,
            merchant_domain=merchant_domain,
            product_url=product_url,
            image_url=image_url or "",
            source_provider=source_provider,
            retrieved_at=now_iso,
            evidence_hash=evidence_hash,
            verification_status=verification_status,
            checkout_capability=checkout_capability,
        )
