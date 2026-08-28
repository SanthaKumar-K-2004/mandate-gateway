"""
S01.1 — BuyerMandate API Contracts.

Request & response schemas for:
  POST /api/mandates
  GET  /api/mandates/{id}
  POST /api/mandates/{id}/revoke
"""

from __future__ import annotations

from datetime import datetime
from typing import FrozenSet

from pydantic import BaseModel, Field

from apps.api.domain.types import Currency, MandateStatus, Region


class MandateCreate(BaseModel):
    """Request payload to issue a new BuyerMandate."""

    buyer_id: str = Field(..., min_length=1, description="Buyer identity (UUID).")
    merchant_scope: set[str] = Field(
        ...,
        min_length=1,
        description="Set of merchant_ids authorized by this mandate.",
    )
    category_scope: set[str] = Field(
        default_factory=set,
        description="Set of product categories authorized (stored lowercase).",
    )
    allowed_regions: set[Region] = Field(
        default_factory=lambda: {Region.IN},
        description="Allowed transaction regions.",
    )
    maximum_amount_paise: int = Field(
        ...,
        ge=0,
        description="Maximum single purchase limit in paise (₹1 = 100 paise).",
    )
    daily_budget_paise: int = Field(
        ...,
        ge=0,
        description="Daily budget cap in paise.",
    )
    currency: Currency = Field(default=Currency.INR)
    autonomous_execution: bool = Field(
        default=True,
        description="True if AI may execute autonomously within limits.",
    )
    expires_at: datetime = Field(
        ...,
        description="UTC datetime after which the mandate is no longer valid.",
    )


class MandateResponse(BaseModel):
    """Response payload representing an active or historical mandate."""

    mandate_id: str
    buyer_id: str
    version: int
    merchant_scope: FrozenSet[str]
    category_scope: FrozenSet[str]
    allowed_regions: FrozenSet[Region]
    maximum_amount_paise: int
    daily_budget_paise: int
    currency: Currency
    autonomous_execution: bool
    status: MandateStatus
    issued_at: datetime
    expires_at: datetime


class MandateRevokeResponse(BaseModel):
    """Response payload when a mandate is revoked."""

    mandate_id: str
    status: MandateStatus
    revoked_at: datetime


class MandateTransitionRequest(BaseModel):
    """Request payload to advance a mandate's lifecycle status."""

    target_status: MandateStatus


class MandateRuleStepResponse(BaseModel):
    """Trace step of mandate rule evaluation."""

    rule_name: str
    passed: bool
    detail: str


class MandateEvaluateResponse(BaseModel):
    """Response payload returned by Mandate Evaluation."""

    valid: bool
    mandate_id: str
    buyer_id: str
    status: MandateStatus
    rejection_reason: str | None = None
    rejection_detail: str | None = None
    evaluated_rules: list[MandateRuleStepResponse]
    evaluated_at: datetime
