"""
Mandate Gateway — Secure Redirect Handoff Manager (M24)
Workstream 10 — Constructs cryptographically signed redirect packages for CHECKOUT_HANDOFF.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any, Dict

from apps.api.commerce.connectors.generic_web import GenericWebCheckoutConnector
from apps.api.commerce.models import VerifiedProduct


class RedirectHandoffError(RuntimeError):
    """Raised when redirect handoff package construction or validation fails."""

    pass


class SecureRedirectHandoffManager:
    """Constructs and validates secure redirect handoff packages."""

    def __init__(self, secret_key: str = "handoff_secret_m24_sec"):
        self.secret_key = secret_key

    def create_handoff_package(
        self, request_id: str, buyer_id: str, product: VerifiedProduct
    ) -> Dict[str, Any]:
        """Create signed redirect handoff package."""
        validated_url = GenericWebCheckoutConnector.validate_handoff_url(product.source_url)
        now_iso = datetime.now(timezone.utc).isoformat()

        raw_payload = (
            f"{request_id}|{buyer_id}|{product.product_id}|"
            f"{product.price.amount_paise}|{validated_url}|{now_iso}"
        )
        sig = hmac.new(
            self.secret_key.encode("utf-8"),
            raw_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return {
            "request_id": request_id,
            "buyer_id": buyer_id,
            "merchant_id": product.merchant.merchant_id,
            "product_id": product.product_id,
            "product_name": product.name,
            "amount_paise": product.price.amount_paise,
            "currency": product.price.currency,
            "handoff_url": validated_url,
            "created_at": now_iso,
            "signature": sig,
            "capability": "CHECKOUT_HANDOFF",
            "disclaimer": "Redirecting to official merchant website. Direct payment API handoff package.",
        }

    def verify_handoff_package(self, package: Dict[str, Any]) -> bool:
        """Verify handoff package signature."""
        try:
            req_id = package["request_id"]
            buyer_id = package["buyer_id"]
            prod_id = package["product_id"]
            amt = package["amount_paise"]
            url = package["handoff_url"]
            created = package["created_at"]
            sig = package["signature"]

            validated_url = GenericWebCheckoutConnector.validate_handoff_url(url)
            raw_payload = f"{req_id}|{buyer_id}|{prod_id}|{amt}|{validated_url}|{created}"
            expected_sig = hmac.new(
                self.secret_key.encode("utf-8"),
                raw_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(sig, expected_sig)
        except Exception:
            return False
