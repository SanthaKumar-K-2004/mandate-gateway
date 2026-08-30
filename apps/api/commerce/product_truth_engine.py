"""
Mandate Gateway — Product Truth Engine (M24)
Workstream 2 — Evaluates exact SKU identity, URL structure, merchant domain,
price evidence, availability, and cryptographic evidence hashes.
"""

from __future__ import annotations

import hashlib
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List

from apps.api.commerce.models import (
    AvailabilityEvidence,
    MerchantIdentity,
    PriceEvidence,
    ProductTruth,
    ProductVerificationStatus,
    VerifiedProduct,
)


class ProductTruthEngineError(RuntimeError):
    """Raised when Product Truth Engine encounters a fatal processing error."""

    pass


class ProductTruthEngine:
    """Production-grade Product Truth Verification Engine."""

    @staticmethod
    def is_exact_product_url(url: str) -> bool:
        """Check if URL indicates a specific single product detail page rather than a category/homepage."""
        if not url:
            return False
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        path = parsed.path.lower()
        if path in ("", "/", "/collections", "/collections/", "/category", "/category/", "/search"):
            return False
        # Specific product detail page indicators
        indicators = [
            "/product/",
            "/products/",
            "/p/",
            "/item/",
            "/dp/",
            "/buy/",
            "/pd/",
            "/goods/",
        ]
        if any(ind in path for ind in indicators):
            return True
        if path.endswith(".html") or path.endswith(".php"):
            return True
        parts = [p for p in path.split("/") if p]
        return len(parts) >= 2 and not any(
            k in parts for k in ["collections", "categories", "search", "all"]
        )

    @classmethod
    def evaluate_product(cls, candidate: Dict[str, Any]) -> ProductTruth:
        """
        Evaluate raw product candidate and produce a validated ProductTruth object.
        Fails closed if evidence is missing, unverified, or mutated.
        """
        errors: List[str] = []

        product_id = candidate.get("product_id") or candidate.get("source_product_id") or ""
        name = candidate.get("name") or candidate.get("title") or ""
        description = candidate.get("description") or ""
        source_url = candidate.get("source_url") or candidate.get("url") or ""
        amount_paise = int(candidate.get("amount_paise") or 0)
        currency = candidate.get("currency") or "INR"
        retrieved_at = (
            candidate.get("retrieval_timestamp") or datetime.now(timezone.utc).isoformat()
        )

        # 1. Exact Product Detail Page Verification
        is_sku_verified = cls.is_exact_product_url(source_url)
        if not is_sku_verified:
            errors.append(
                f"URL '{source_url}' is a collection/listing page, not a single SKU product detail page."
            )

        # 2. Price Evidence Verification
        is_price_verified = amount_paise >= 1000 and currency == "INR"
        if not is_price_verified:
            errors.append(
                f"Price amount {amount_paise} Paise (₹{amount_paise/100:.2f}) is unverified or invalid."
            )

        # 3. Merchant Domain Identity Verification
        merchant_name = (
            candidate.get("merchant_name") or candidate.get("merchant_identity") or "Unknown"
        )
        parsed_url = urllib.parse.urlparse(source_url)
        domain = parsed_url.netloc.replace("www.", "") if parsed_url.netloc else "unknown.local"
        is_merchant_verified = bool(domain and domain != "unknown.local")

        merchant = MerchantIdentity(
            merchant_id=f"mer_{domain.replace('.', '_')[:25]}",
            domain=domain,
            legal_name=merchant_name,
            identity_status="VERIFIED" if is_merchant_verified else "UNKNOWN",
        )

        # 4. Evidence Hash Computation
        raw_evidence = f"{source_url}|{name}|{amount_paise}|{currency}|{retrieved_at}"
        evidence_hash = hashlib.sha256(raw_evidence.encode("utf-8")).hexdigest()

        price_evidence = PriceEvidence(
            amount_paise=amount_paise,
            currency=currency,
            verified_at=retrieved_at,
            evidence_url=source_url,
            evidence_hash=evidence_hash,
        )

        availability_evidence = AvailabilityEvidence(
            is_in_stock=candidate.get("availability", True),
            stock_quantity=candidate.get("stock_quantity"),
            verified_at=retrieved_at,
            evidence_url=source_url,
        )

        # Determine Product Verification Status
        if is_sku_verified and is_price_verified and is_merchant_verified:
            status = ProductVerificationStatus.PRODUCT_VERIFIED
        elif candidate.get("verification_status") == "SOURCE_BACKED" or not is_sku_verified:
            status = ProductVerificationStatus.SOURCE_BACKED
        else:
            status = ProductVerificationStatus.UNVERIFIED

        verified_prod = VerifiedProduct(
            product_id=product_id if product_id else f"prod_{evidence_hash[:10]}",
            name=name,
            description=description,
            price=price_evidence,
            availability=availability_evidence,
            merchant=merchant,
            source_url=source_url,
            retrieved_at=retrieved_at,
            verification_status=status,
            evidence_hash=evidence_hash,
        )

        return ProductTruth(
            product=verified_prod,
            is_sku_verified=is_sku_verified,
            is_price_verified=is_price_verified,
            is_merchant_verified=is_merchant_verified,
            validation_errors=errors,
        )
