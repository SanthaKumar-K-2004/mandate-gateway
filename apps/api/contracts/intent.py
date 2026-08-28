"""
S01.2 — Commerce Intent Normalization API Contracts.

Request & Response DTO schemas for POST /api/intents/normalize.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from apps.api.contracts.transaction import CartItemProposal
from apps.api.domain.types import Currency, McpOperation, Region


class ProposalNormalizeRequest(BaseModel):
    """API Request DTO to normalize an untrusted AI proposal."""

    buyer_id: str = Field(..., min_length=1)
    merchant_id: str = Field(..., min_length=1)
    mandate_id: str = Field(..., min_length=1)
    raw_prompt: str = Field(..., min_length=1, max_length=5000)
    items: list[CartItemProposal] = Field(..., min_length=1)
    operation: McpOperation = Field(default=McpOperation.CREATE_ORDER)
    currency: Currency = Field(default=Currency.INR)
    region: Region = Field(default=Region.IN)
    tax_paise: int = Field(default=0, ge=0)
    shipping_paise: int = Field(default=0, ge=0)
    total_paise: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalCartItemResponse(BaseModel):
    """Line-item representation in canonical cart response."""

    product_id: str
    merchant_id: str
    name: str
    category: str
    quantity: int
    unit_price_paise: int
    currency: Currency
    subtotal_paise: int


class CanonicalCartResponse(BaseModel):
    """Canonical cart snapshot response."""

    cart_id: str
    merchant_id: str
    mandate_id: str
    currency: Currency
    items: list[CanonicalCartItemResponse]
    tax_paise: int
    shipping_paise: int
    total_paise: int
    cart_hash: str
    created_at: datetime


class CommerceIntentResponse(BaseModel):
    """Canonical CommerceIntent representation response."""

    intent_id: str
    buyer_id: str
    target_merchant_id: str | None
    target_category: str | None
    raw_prompt: str
    max_budget_paise: int | None
    currency: Currency
    region: Region
    metadata: dict[str, Any]
    created_at: datetime


class ProposalNormalizeResponse(BaseModel):
    """Response payload returned by POST /api/intents/normalize."""

    normalized: bool = True
    intent: CommerceIntentResponse
    cart: CanonicalCartResponse
    normalized_at: datetime
