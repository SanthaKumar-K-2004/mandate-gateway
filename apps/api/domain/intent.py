"""
S01.1 — Commerce Intent Contract.

Represents a structured natural-language or structured intent payload
submitted by an AI shopping agent or user (Section 6, PROJECT_CONTEXT.md).

Data contract only — normalization behavior belongs to S01.2.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from apps.api.domain.types import Currency, Region


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class CommerceIntent(BaseModel):
    """
    Contract representing parsed buyer shopping intent.

    Immutable contract (frozen=True).
    """

    model_config = {"frozen": True}

    intent_id: str = Field(default_factory=_new_uuid)
    buyer_id: str = Field(..., min_length=1, description="Buyer identity (UUID).")
    raw_prompt: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="[UNTRUSTED] Raw natural-language shopping prompt.",
    )
    target_category: str | None = Field(default=None, description="Target product category.")
    target_merchant_id: str | None = Field(default=None, description="Target merchant ID.")
    max_budget_paise: int | None = Field(
        default=None, ge=0, description="Intended maximum budget in paise."
    )
    currency: Currency = Field(default=Currency.INR)
    region: Region = Field(default=Region.IN)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)
