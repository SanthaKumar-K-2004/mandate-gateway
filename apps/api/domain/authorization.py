"""
S01.1 — Authorization Request & Decision Contracts.

Pure data contracts representing a request to the Mandate Gateway
and the resulting decision payload (Section 11, PROJECT_CONTEXT.md).

Data contracts only — evaluation logic belongs to S01.5.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from apps.api.contracts.transaction import StepUpDiff
from apps.api.domain.types import (
    Currency,
    McpOperation,
    PolicyDecision,
    Region,
    RejectionReason,
)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class AuthorizationRequest(BaseModel):
    """Contract for a gateway authorization request."""

    model_config = {"frozen": True}

    request_id: str = Field(default_factory=_new_uuid)
    buyer_id: str = Field(..., min_length=1)
    merchant_id: str = Field(..., min_length=1)
    mandate_id: str = Field(..., min_length=1)
    operation: McpOperation = Field(default=McpOperation.CREATE_ORDER)
    amount_paise: int = Field(..., ge=0)
    currency: Currency = Field(default=Currency.INR)
    region: Region = Field(default=Region.IN)
    cart_id: str | None = Field(default=None)
    cart_hash: str | None = Field(default=None)
    idempotency_key: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=_utc_now)


class AuthorizationDecision(BaseModel):
    """Contract for a gateway authorization decision outcome."""

    model_config = {"frozen": True}

    decision_id: str = Field(default_factory=_new_uuid)
    request_id: str = Field(..., min_length=1)
    transaction_id: str | None = Field(default=None)
    decision: PolicyDecision
    rejection_reason: RejectionReason | None = Field(default=None)
    rejection_detail: str | None = Field(default=None)
    step_up_diff: StepUpDiff | None = Field(default=None)
    checks_passed: tuple[str, ...] = Field(default_factory=tuple)
    checks_failed: tuple[str, ...] = Field(default_factory=tuple)
    nonce: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utc_now)


class ExecutionRequest(BaseModel):
    """Contract for translating an authorized decision into a Razorpay MCP execution request."""

    model_config = {"frozen": True}

    execution_id: str = Field(default_factory=_new_uuid)
    transaction_id: str = Field(..., min_length=1)
    nonce: str = Field(..., min_length=16)
    cart_hash: str = Field(..., min_length=64, max_length=64)
    operation: McpOperation
    amount_paise: int = Field(..., ge=0)
    currency: Currency = Field(default=Currency.INR)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)
