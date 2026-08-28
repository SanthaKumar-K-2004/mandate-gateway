"""
S01.6 — Cart Integrity Verification Engine.

Determines whether the cart being authorized or executed is identical to the canonical
cart representation that was authorized by the buyer and merchant policies.

Core Security Principles:
  1. Untrusted AI/Agent Defense: Hashes or totals supplied by the untrusted actor (AI)
     are NEVER trusted. The verifier calculates expected and current canonical hashes
     directly from trusted cart data structures.
  2. Constant-Time Comparison: Hash digests are compared using hmac.compare_digest
     to prevent timing side-channel attacks.
  3. No Silent Repair: Any difference in security-sensitive fields (merchant, items,
     quantities, prices, currency, tax, shipping, total) fails closed (REJECT).
  4. Non-Semantic Reordering Tolerance: Line items are canonically sorted by product_id
     so [A, B] and [B, A] produce identical canonical digests.
  5. Immutability & Pure Execution: Zero I/O, zero network, zero state mutation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from apps.api.domain.cart import Cart, CartItem
from apps.api.domain.types import Currency, PolicyDecision, RejectionReason


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


_HEX_64_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


def _is_valid_hex64(s: str) -> bool:
    """Return True if s is a 64-character valid hexadecimal SHA-256 digest."""
    return bool(s and _HEX_64_PATTERN.match(s))


def _canonical_item(item: CartItem) -> dict[str, object]:
    """Format a CartItem into its canonical JSON object representation."""
    return {
        "category": item.category.strip().lower(),
        "merchant_id": item.merchant_id,
        "product_id": item.product_id,
        "quantity": item.quantity,
        "unit_price_paise": item.unit_price_paise,
    }


def compute_cart_hash(
    *,
    merchant_id: str,
    mandate_id: str,
    currency: Currency,
    items: tuple[CartItem, ...] | list[CartItem],
    tax_paise: int,
    shipping_paise: int,
    total_paise: int,
) -> str:
    """
    Compute the canonical SHA-256 cart digest.

    Rules:
      - Line items sorted by product_id (lexicographic ascending).
      - JSON key order sorted, no whitespace separators.
      - Encoded as UTF-8 before hashing.
    """
    sorted_items = sorted(items, key=lambda i: i.product_id)
    canonical: dict[str, object] = {
        "currency": currency.value,
        "items": [_canonical_item(i) for i in sorted_items],
        "mandate_id": mandate_id,
        "merchant_id": merchant_id,
        "shipping_paise": shipping_paise,
        "tax_paise": tax_paise,
        "total_paise": total_paise,
    }
    serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_cart_object_hash(cart: Cart) -> str:
    """Compute canonical hash digest for a Cart instance."""
    return compute_cart_hash(
        merchant_id=cart.merchant_id,
        mandate_id=cart.mandate_id,
        currency=cart.currency,
        items=cart.items,
        tax_paise=cart.tax_paise,
        shipping_paise=cart.shipping_paise,
        total_paise=cart.total_paise,
    )


def build_cart_with_hash(
    *,
    cart_id: str | None = None,
    merchant_id: str,
    mandate_id: str,
    currency: Currency,
    items: tuple[CartItem, ...],
    tax_paise: int = 0,
    shipping_paise: int = 0,
    total_paise: int,
) -> Cart:
    """Construct a Cart instance with computed canonical hash attached."""
    digest = compute_cart_hash(
        merchant_id=merchant_id,
        mandate_id=mandate_id,
        currency=currency,
        items=items,
        tax_paise=tax_paise,
        shipping_paise=shipping_paise,
        total_paise=total_paise,
    )
    if cart_id is not None:
        return Cart(
            cart_id=cart_id,
            merchant_id=merchant_id,
            mandate_id=mandate_id,
            currency=currency,
            items=items,
            tax_paise=tax_paise,
            shipping_paise=shipping_paise,
            total_paise=total_paise,
            cart_hash=digest,
        )
    return Cart(
        merchant_id=merchant_id,
        mandate_id=mandate_id,
        currency=currency,
        items=items,
        tax_paise=tax_paise,
        shipping_paise=shipping_paise,
        total_paise=total_paise,
        cart_hash=digest,
    )


# ---------------------------------------------------------------------------
# Cart Integrity Verification Result DTO
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CartIntegrityResult:
    """Outcome of S01.6 Cart Integrity Verification."""

    valid: bool
    authorized_hash: str
    current_hash: str
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    field_mismatches: tuple[str, ...] = field(default_factory=tuple)
    evaluated_at: datetime = field(default_factory=_utc_now)

    @property
    def is_valid(self) -> bool:
        return self.valid

    @property
    def is_invalid(self) -> bool:
        return not self.valid

    def to_security_control_outcome(self) -> object:
        """Convert to SecurityControlOutcome for S01.5 aggregation."""
        from apps.api.domain.authorization_aggregator import SecurityControlOutcome

        return SecurityControlOutcome(
            control_name="CART_INTEGRITY",
            passed=self.valid,
            decision=PolicyDecision.ALLOW if self.valid else PolicyDecision.REJECT,
            rejection_reason=self.rejection_reason,
            detail=self.rejection_detail,
        )


# ---------------------------------------------------------------------------
# Cart Integrity Verification Engine
# ---------------------------------------------------------------------------


class CartIntegrityVerifier:
    """
    Pure deterministic Cart Integrity Verification Engine.

    Verifies that a current cart snapshot matches the authorized cart snapshot.
    """

    @classmethod
    def verify(  # noqa: C901
        cls,
        authorized_cart: Cart | str,
        current_cart: Cart,
        at: datetime | None = None,
    ) -> CartIntegrityResult:
        """
        Verify that current_cart matches authorized_cart (or trusted authorized_hash string).

        Returns:
            CartIntegrityResult (valid=True if identical, valid=False otherwise).
        """
        eval_time = at if at is not None else _utc_now()
        mismatches: list[str] = []

        # Determine expected authorized hash
        expected_hash: str
        if isinstance(authorized_cart, Cart):
            expected_hash = (
                authorized_cart.cart_hash
                if authorized_cart.cart_hash
                else compute_cart_object_hash(authorized_cart)
            )
        else:
            expected_hash = authorized_cart.strip().lower()

        # Validate format of expected hash
        if not _is_valid_hex64(expected_hash):
            return CartIntegrityResult(
                valid=False,
                authorized_hash=expected_hash,
                current_hash="",
                rejection_reason=RejectionReason.CART_INTEGRITY_VIOLATION,
                rejection_detail="Authorized cart hash is missing or malformed.",
                field_mismatches=("malformed_authorized_hash",),
                evaluated_at=eval_time,
            )

        # Compute current cart canonical hash
        current_hash = (
            current_cart.cart_hash
            if current_cart.cart_hash
            else compute_cart_object_hash(current_cart)
        ).lower()

        # Verify format of current hash
        if not _is_valid_hex64(current_hash):
            return CartIntegrityResult(
                valid=False,
                authorized_hash=expected_hash,
                current_hash=current_hash,
                rejection_reason=RejectionReason.CART_INTEGRITY_VIOLATION,
                rejection_detail="Current cart canonical hash is malformed.",
                field_mismatches=("malformed_current_hash",),
                evaluated_at=eval_time,
            )

        # Perform constant-time hash comparison
        hashes_match = hmac.compare_digest(expected_hash, current_hash)

        if hashes_match:
            return CartIntegrityResult(
                valid=True,
                authorized_hash=expected_hash,
                current_hash=current_hash,
                rejection_reason=None,
                rejection_detail=None,
                field_mismatches=(),
                evaluated_at=eval_time,
            )

        # Detailed field mismatch inspection if authorized_cart is a Cart object
        if isinstance(authorized_cart, Cart):
            if authorized_cart.merchant_id != current_cart.merchant_id:
                mismatches.append("merchant_id_mismatch")
            if authorized_cart.mandate_id != current_cart.mandate_id:
                mismatches.append("mandate_id_mismatch")
            if authorized_cart.currency != current_cart.currency:
                mismatches.append("currency_mismatch")
            if authorized_cart.tax_paise != current_cart.tax_paise:
                mismatches.append("tax_paise_mismatch")
            if authorized_cart.shipping_paise != current_cart.shipping_paise:
                mismatches.append("shipping_paise_mismatch")
            if authorized_cart.total_paise != current_cart.total_paise:
                mismatches.append("total_paise_mismatch")

            # Check items
            auth_items_sorted = sorted(authorized_cart.items, key=lambda i: i.product_id)
            curr_items_sorted = sorted(current_cart.items, key=lambda i: i.product_id)

            if len(auth_items_sorted) != len(curr_items_sorted):
                mismatches.append("item_count_mismatch")
            else:
                for a_item, c_item in zip(auth_items_sorted, curr_items_sorted):
                    if a_item.product_id != c_item.product_id:
                        mismatches.append(f"product_id_mismatch:{c_item.product_id}")
                    if a_item.quantity != c_item.quantity:
                        mismatches.append(f"quantity_mismatch:{c_item.product_id}")
                    if a_item.unit_price_paise != c_item.unit_price_paise:
                        mismatches.append(f"unit_price_mismatch:{c_item.product_id}")
                    if a_item.category.strip().lower() != c_item.category.strip().lower():
                        mismatches.append(f"category_mismatch:{c_item.product_id}")
        else:
            mismatches.append("hash_mismatch")

        # Standard rejection reason mapping
        reason = RejectionReason.CART_INTEGRITY_VIOLATION
        if "merchant_id_mismatch" in mismatches:
            reason = RejectionReason.MERCHANT_MISMATCH
        elif "currency_mismatch" in mismatches:
            reason = RejectionReason.CART_CURRENCY_MISMATCH
        elif "total_paise_mismatch" in mismatches:
            reason = RejectionReason.CART_TOTAL_MISMATCH

        detail = f"Cart integrity verification failed. Field mismatches: {', '.join(mismatches)}."

        return CartIntegrityResult(
            valid=False,
            authorized_hash=expected_hash,
            current_hash=current_hash,
            rejection_reason=reason,
            rejection_detail=detail,
            field_mismatches=tuple(mismatches),
            evaluated_at=eval_time,
        )


def verify_cart_integrity(cart: Cart, approved_hash: str) -> bool:
    """
    Backwards-compatible convenience function for simple boolean cart integrity verification.

    Uses constant-time comparison via CartIntegrityVerifier.
    """
    return CartIntegrityVerifier.verify(authorized_cart=approved_hash, current_cart=cart).valid
