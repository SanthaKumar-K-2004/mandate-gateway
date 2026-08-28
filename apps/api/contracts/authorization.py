"""
S01.5 — Authorization Aggregation API Contracts.

Request & Response DTO schemas for gateway authorization endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from apps.api.contracts.transaction import StepUpDiff
from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.types import (
    Currency,
    McpOperation,
    PolicyDecision,
    Region,
    RejectionReason,
)


class AuthorizationEvaluateRequest(BaseModel):
    """Request payload to perform gateway authorization aggregation."""

    request_id: str = Field(..., min_length=1, description="Unique authorization request UUID.")
    buyer_id: str = Field(..., min_length=1, description="Buyer identity UUID.")
    merchant_id: str = Field(..., min_length=1, description="Merchant identity ID.")
    mandate_id: str = Field(..., min_length=1, description="Buyer mandate UUID.")
    operation: McpOperation = Field(default=McpOperation.CREATE_ORDER)
    amount_paise: int = Field(..., ge=0, description="Purchase amount in paise.")
    currency: Currency = Field(default=Currency.INR)
    region: Region = Field(default=Region.IN)
    cart_id: str = Field(..., min_length=1)
    cart_hash: str = Field(..., min_length=64, max_length=64)
    idempotency_key: str = Field(..., min_length=1)


class AuthorizationEvaluateResponse(BaseModel):
    """Response payload returned by Authorization Aggregator."""

    decision_id: str
    request_id: str
    decision: PolicyDecision
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    step_up_diff: StepUpDiff | None = None
    checks_passed: list[str]
    checks_failed: list[str]
    evaluated_at: datetime


class AuthorizationResult(BaseModel):
    """Domain & API contract representing the aggregated output of S01.5 Authorization Aggregator."""

    decision: PolicyDecision
    control_outcomes: list[SecurityControlOutcome] = Field(default_factory=list)
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    decision_trace: dict[str, Any] = Field(default_factory=dict)
