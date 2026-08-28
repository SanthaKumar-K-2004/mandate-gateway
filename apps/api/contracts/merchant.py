"""
S01.1 — Merchant & MerchantPolicy API Contracts.

Request & response schemas for:
  POST /api/merchants
  GET  /api/merchants/{id}
  POST /api/merchants/{id}/policy
  GET  /api/merchants/{id}/policy
  PUT  /api/merchants/{id}/policy
"""

from __future__ import annotations

from datetime import datetime
from typing import FrozenSet

from pydantic import BaseModel, Field

from apps.api.domain.types import Currency, McpOperation, Region


class MerchantCreate(BaseModel):
    """Request payload to create a new merchant."""

    name: str = Field(..., min_length=1, max_length=255, description="Merchant display name.")
    razorpay_account_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Razorpay account ID (test mode).",
    )


class MerchantResponse(BaseModel):
    """Response payload representing a registered merchant."""

    merchant_id: str
    name: str
    razorpay_account_id: str
    created_at: datetime


class PolicyCreate(BaseModel):
    """Request payload to create or update a merchant's AI commerce policy."""

    ai_commerce_enabled: bool = Field(
        ...,
        description="Master switch enabling or disabling AI commerce for this merchant.",
    )
    currency: Currency = Field(default=Currency.INR)
    allowed_categories: set[str] = Field(
        default_factory=set,
        description="Set of product categories permitted for AI buyers.",
    )
    autonomous_purchase_limit_paise: int = Field(
        ...,
        ge=0,
        description="Maximum autonomous single-purchase limit in paise.",
    )
    step_up_threshold_paise: int = Field(
        ...,
        ge=0,
        description="Transaction amount in paise above which step-up approval is required.",
    )
    max_step_up_percent: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Maximum step-up price increase allowed over mandate cap (default 10%).",
    )
    allowed_regions: set[Region] = Field(
        default_factory=lambda: {Region.IN},
        description="Set of allowed regions.",
    )
    allowed_operations: set[McpOperation] = Field(
        default_factory=lambda: {
            McpOperation.CREATE_ORDER,
            McpOperation.CREATE_PAYMENT_LINK,
            McpOperation.FETCH_PAYMENT,
        },
        description="MCP operations explicitly permitted for AI buyers.",
    )
    blocked_operations: set[McpOperation] = Field(
        default_factory=lambda: {
            McpOperation.PAYOUT,
            McpOperation.SETTLEMENT,
            McpOperation.BANK_TRANSFER,
        },
        description="MCP operations explicitly blocked.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional UTC expiry time.",
    )


class PolicyResponse(BaseModel):
    """Response payload representing an active merchant policy."""

    policy_id: str
    merchant_id: str
    policy_version: int
    ai_commerce_enabled: bool
    currency: Currency
    allowed_categories: FrozenSet[str]
    autonomous_purchase_limit_paise: int
    step_up_threshold_paise: int
    max_step_up_percent: int
    allowed_regions: FrozenSet[Region]
    allowed_operations: FrozenSet[McpOperation]
    blocked_operations: FrozenSet[McpOperation]
    created_at: datetime
    expires_at: datetime | None


class RuleEvaluationStepResponse(BaseModel):
    """Trace step of rule evaluation."""

    rule_name: str
    passed: bool
    detail: str


class PolicyEvaluateResponse(BaseModel):
    """Response payload returned by Merchant Policy evaluation."""

    decision: str  # ALLOW or REJECT
    merchant_id: str
    policy_id: str
    policy_version: int
    rejection_reason: str | None = None
    rejection_detail: str | None = None
    evaluated_rules: list[RuleEvaluationStepResponse]
    evaluated_at: datetime
