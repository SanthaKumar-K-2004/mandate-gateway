"""
S01.1 — BuyerMandate Data Contract.

Represents explicit buyer authorization (Section 9, PROJECT_CONTEXT.md).

Mandate fields:
  mandate_id, buyer_id, merchant_scope, category_scope,
  maximum_amount_paise, currency, daily_budget_paise, autonomous_execution,
  issued_at, expires_at, version, status.

Data contract only — state machine lifecycle transitions belong to S01.4 (mandate_lifecycle.py).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import FrozenSet

from pydantic import BaseModel, Field, field_validator, model_validator

from apps.api.domain.types import Currency, MandateStatus, Region


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class BuyerMandate(BaseModel):
    """
    Explicit buyer authorization for AI-driven commerce.

    Immutable contract (frozen=True).
    All monetary limits are stored as integer paise to prevent float rounding errors.
    """

    model_config = {"frozen": True}

    mandate_id: str = Field(default_factory=_new_uuid)
    buyer_id: str = Field(..., min_length=1, description="Buyer identity (UUID).")
    version: int = Field(default=1, ge=1, description="Mandate version (immutable).")

    merchant_scope: FrozenSet[str] = Field(
        default=frozenset(),
        description="Set of merchant_id values this mandate authorizes.",
    )
    category_scope: FrozenSet[str] = Field(
        default=frozenset(),
        description="Set of product categories authorized (stored lowercase).",
    )
    allowed_regions: FrozenSet[Region] = Field(
        default=frozenset(),
        description="Allowed transaction regions.",
    )

    maximum_amount_paise: int = Field(
        ...,
        ge=0,
        description="Maximum single transaction amount in paise.",
    )
    daily_budget_paise: int = Field(
        ...,
        ge=0,
        description="Maximum cumulative spend per calendar day in paise.",
    )
    currency: Currency = Field(..., description="Authorized currency.")

    autonomous_execution: bool = Field(
        ...,
        description="True if AI may autonomously execute purchases within limits.",
    )

    issued_at: datetime = Field(default_factory=_utc_now)
    expires_at: datetime = Field(
        ...,
        description="UTC datetime after which this mandate is no longer valid.",
    )

    status: MandateStatus = Field(default=MandateStatus.DRAFT)

    @model_validator(mode="after")
    def _validate_expiry(self) -> BuyerMandate:
        if self.expires_at <= self.issued_at:
            raise ValueError(
                f"expires_at ({self.expires_at.isoformat()}) must be after "
                f"issued_at ({self.issued_at.isoformat()})."
            )
        if self.daily_budget_paise < self.maximum_amount_paise:
            raise ValueError(
                f"daily_budget_paise ({self.daily_budget_paise}) must be >= "
                f"maximum_amount_paise ({self.maximum_amount_paise})."
            )
        return self

    @field_validator("buyer_id", mode="before")
    @classmethod
    def strip_buyer_id(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("category_scope", mode="before")
    @classmethod
    def normalize_categories(cls, v: object) -> object:
        if isinstance(v, (list, set, frozenset)):
            return frozenset(c.strip().lower() for c in v if isinstance(c, str))
        return v

    def is_active(self, at: datetime | None = None) -> bool:
        """Return True if mandate status is ACTIVE and not expired."""
        check_time = at if at is not None else _utc_now()
        return self.status is MandateStatus.ACTIVE and check_time < self.expires_at

    def authorizes_merchant(self, merchant_id: str) -> bool:
        """Return True if this mandate covers merchant_id."""
        return merchant_id in self.merchant_scope

    def authorizes_category(self, category: str) -> bool:
        """Return True if product category is within scope."""
        return category.strip().lower() in self.category_scope

    def authorizes_amount(self, amount_paise: int) -> bool:
        """Return True if amount_paise <= maximum_amount_paise."""
        return amount_paise <= self.maximum_amount_paise

    def authorizes_region(self, region: Region) -> bool:
        """Return True if region is permitted."""
        return region in self.allowed_regions
