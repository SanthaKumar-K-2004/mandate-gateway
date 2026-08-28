"""
S01.11 — Payment Execution API Contracts.

Public API request & response contracts for payment execution:
  POST /api/transactions/{id}/execute
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from apps.api.domain.types import (
    Currency,
    McpOperation,
    PaymentResultState,
    RejectionReason,
    TransactionState,
)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class PaymentExecuteProposalRequest(BaseModel):
    """
    Untrusted execution proposal payload submitted by AI agent or client.

    All fields are treated as UNTRUSTED proposals and verified strictly
    against authoritative transaction & authorization records. Any untrusted
    authority fields in `untrusted_metadata` (e.g. `admin_override`, `bypass_auth`)
    are strictly IGNORED by the gateway.
    """

    transaction_id: str = Field(..., min_length=1)
    merchant_id: str = Field(..., min_length=1)
    buyer_id: str = Field(..., min_length=1)
    mandate_id: str = Field(..., min_length=1)
    amount_paise: int = Field(..., ge=0)
    currency: Currency = Field(default=Currency.INR)
    cart_hash: str = Field(..., min_length=1)
    operation: McpOperation = Field(default=McpOperation.CREATE_ORDER)
    idempotency_key: str = Field(..., min_length=1)
    untrusted_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Untrusted AI or client metadata. Never trusted for policy overrides.",
    )


class PaymentExecuteResponse(BaseModel):
    """
    Public response payload returned by the Mandate Gateway execution boundary.

    Zero credentials, authorization tokens, or internal provider secrets are exposed.
    """

    success: bool
    transaction_id: str
    state: TransactionState
    external_reference: str | None = Field(
        default=None,
        description="Razorpay order/payment ID if executed successfully.",
    )
    failure_code: RejectionReason | None = Field(
        default=None,
        description="Structured rejection reason if execution failed.",
    )
    failure_category: str | None = Field(
        default=None,
        description="Internal failure category (e.g., AUTHORIZATION_FAILED, TIMEOUT).",
    )
    safe_message: str = Field(..., min_length=1)
    idempotent_replay: bool = Field(
        default=False,
        description="True if returning cached result from duplicate execution request.",
    )
    provider_status: PaymentResultState | None = Field(
        default=None,
        description="Razorpay provider payment result status.",
    )
    executed_at: datetime = Field(default_factory=_utc_now)
