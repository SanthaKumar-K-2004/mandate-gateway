"""
S01.1 — Cart & CartItem Data Contracts.

Structured cart proposal contract (Section 10, PROJECT_CONTEXT.md).

Data contracts only — canonical hash calculation & integrity evaluation belong to S01.6 (cart_integrity.py).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, model_validator

from apps.api.domain.types import Currency


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class CartItem(BaseModel):
    """A single line-item in a cart proposal."""

    model_config = {"frozen": True}

    product_id: str = Field(..., min_length=1)
    merchant_id: str = Field(..., min_length=1)
    name: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="[UNTRUSTED] Product name — informational only.",
    )
    category: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(..., ge=1, description="Units ordered.")
    unit_price_paise: int = Field(..., ge=0, description="Per-unit price in paise.")
    currency: Currency

    def subtotal_paise(self) -> int:
        """Return quantity * unit_price_paise."""
        return self.quantity * self.unit_price_paise


class Cart(BaseModel):
    """
    A structured cart proposal contract.

    All monetary fields are integer paise.
    Immutable contract (frozen=True).
    """

    model_config = {"frozen": True}

    cart_id: str = Field(default_factory=_new_uuid)
    merchant_id: str = Field(..., min_length=1)
    mandate_id: str = Field(..., min_length=1)
    currency: Currency

    items: tuple[CartItem, ...] = Field(
        ...,
        min_length=1,
        description="Ordered list of cart line-items.",
    )

    tax_paise: int = Field(default=0, ge=0, description="Total tax in paise.")
    shipping_paise: int = Field(default=0, ge=0, description="Shipping cost in paise.")
    total_paise: int = Field(
        ...,
        ge=0,
        description="Grand total in paise (items subtotal + tax + shipping).",
    )

    created_at: datetime = Field(default_factory=_utc_now)
    cart_hash: str = Field(default="", description="SHA-256 hex digest of canonical cart.")

    @model_validator(mode="after")
    def _validate_items(self) -> Cart:
        # Validate currency & merchant consistency across items
        for item in self.items:
            if item.currency is not self.currency:
                raise ValueError(
                    f"Item {item.product_id!r} currency {item.currency.value!r} "
                    f"does not match cart currency {self.currency.value!r}."
                )
            if item.merchant_id != self.merchant_id:
                raise ValueError(
                    f"Item {item.product_id!r} merchant_id {item.merchant_id!r} "
                    f"does not match cart merchant_id {self.merchant_id!r}."
                )

        # Validate computed total
        computed_items_total = sum(i.subtotal_paise() for i in self.items)
        expected_total = computed_items_total + self.tax_paise + self.shipping_paise
        if self.total_paise != expected_total:
            raise ValueError(
                f"Cart total mismatch: declared {self.total_paise} paise, "
                f"computed {expected_total} paise."
            )
        return self
