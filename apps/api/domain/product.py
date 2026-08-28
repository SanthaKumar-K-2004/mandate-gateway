"""
S01.1 — Product Catalog Domain Model.

Product fields (Section 8, PROJECT_CONTEXT.md):
  product_id, merchant_id, name, description, category, price,
  currency, availability, metadata, created_at, updated_at.

Security rule (Section 8, PROJECT_CONTEXT.md):
  Catalog data is UNTRUSTED.
  A product description may contain malicious prompt-injection text.
  The Gateway must never treat catalog text as authorization.

This model enforces the untrusted boundary by:
  - Marking all catalog text fields as untrusted.
  - Providing no methods that evaluate or interpret catalog text.
  - Ensuring price is stored as paise (no float rounding).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

from apps.api.domain.types import Currency


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Product(BaseModel):
    """
    Product in the untrusted external catalog.

    SECURITY INVARIANT: The description and name fields are untrusted.
    They may contain adversarial prompt-injection text.
    No policy decision must ever be derived from these fields.
    """

    model_config = {"frozen": True}

    product_id: str = Field(default_factory=_new_uuid)
    merchant_id: str = Field(..., min_length=1)

    # Untrusted catalog fields (marked for clarity)
    name: str = Field(..., min_length=1, max_length=500, description="[UNTRUSTED] Product name.")
    description: str = Field(
        ...,
        max_length=5000,
        description=(
            "[UNTRUSTED] Product description. "
            "May contain adversarial prompt-injection text. "
            "Must never be evaluated as authorization input."
        ),
    )
    category: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Product category (used for policy matching — normalized to lowercase).",
    )

    # Monetary fields (price stored in paise)
    price_paise: int = Field(
        ...,
        ge=0,
        description="Product price in paise (₹1 = 100 paise). Non-negative.",
    )
    currency: Currency = Field(..., description="Price currency.")

    availability: bool = Field(..., description="True if the product is currently available.")

    # Free-form metadata (also untrusted — same security rule applies)
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="[UNTRUSTED] Arbitrary product metadata. Never authorize based on this.",
    )

    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: object) -> object:
        """Normalize category to lowercase to simplify policy matching."""
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("merchant_id", mode="before")
    @classmethod
    def strip_merchant_id(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    def price_rupees(self) -> float:
        """Return price as rupees (display only — do not use for calculations)."""
        return self.price_paise / 100.0
