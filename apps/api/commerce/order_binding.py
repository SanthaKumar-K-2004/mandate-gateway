"""
Mandate Gateway — Commerce Order Binder (M25)
Workstream 2 — Cryptographically binds purchase plan, buyer, merchant, product, quantity,
amount, merchant order, and payment reference to prevent substitution attacks.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Dict


class OrderBindingError(RuntimeError):
    """Raised when order binding verification fails or substitution is detected."""

    pass


class CommerceOrderBinder:
    """Cryptographic Cart, Order, and Payment Binding Engine."""

    def __init__(self, secret_key: str = "order_binding_sec_key_m25") -> None:
        self.secret_key = secret_key

    def compute_binding_hash(
        self,
        purchase_request_id: str,
        merchant_id: str,
        buyer_id: str,
        product_id: str,
        quantity: int,
        amount_paise: int,
        currency: str,
        merchant_order_id: str,
        payment_reference: str,
        plan_hash: str,
    ) -> str:
        """Compute cryptographic SHA-256 order binding hash."""
        raw_payload = (
            f"{purchase_request_id}|{merchant_id}|{buyer_id}|{product_id}|"
            f"{quantity}|{amount_paise}|{currency}|{merchant_order_id}|"
            f"{payment_reference}|{plan_hash}"
        )
        return hmac.new(
            self.secret_key.encode("utf-8"),
            raw_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def verify_binding(
        self,
        binding_payload: Dict[str, Any],
        expected_binding_hash: str,
    ) -> bool:
        """Verify binding payload matches expected cryptographic hash digest."""
        try:
            computed = self.compute_binding_hash(
                purchase_request_id=binding_payload["purchase_request_id"],
                merchant_id=binding_payload["merchant_id"],
                buyer_id=binding_payload["buyer_id"],
                product_id=binding_payload["product_id"],
                quantity=int(binding_payload.get("quantity", 1)),
                amount_paise=int(binding_payload["amount_paise"]),
                currency=binding_payload.get("currency", "INR"),
                merchant_order_id=binding_payload["merchant_order_id"],
                payment_reference=binding_payload["payment_reference"],
                plan_hash=binding_payload["plan_hash"],
            )
            return hmac.compare_digest(computed, expected_binding_hash)
        except Exception:
            return False
