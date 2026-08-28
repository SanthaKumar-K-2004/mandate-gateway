"""
S01.1 — Purchase Proposal & Transaction API Contracts.

Request & response schemas for:
  POST /api/purchase-proposals
  GET  /api/transactions/{id}
  POST /api/transactions/{id}/approve
  POST /api/transactions/{id}/reject
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from apps.api.domain.types import (
    Currency,
    McpOperation,
    PolicyDecision,
    RejectionReason,
    TransactionState,
)


class CartItemProposal(BaseModel):
    """Line-item proposal from the AI agent."""

    product_id: str = Field(..., min_length=1)
    merchant_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=500, description="[UNTRUSTED] Product name.")
    category: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(..., ge=1)
    unit_price_paise: int = Field(..., ge=0)
    currency: Currency = Field(default=Currency.INR)


class PurchaseProposalRequest(BaseModel):
    """
    Request payload submitted by the AI agent to initiate a purchase authorization.

    Contains the buyer identity, merchant identity, mandate ID, operation requested,
    and proposed cart items.
    """

    buyer_id: str = Field(..., min_length=1)
    merchant_id: str = Field(..., min_length=1)
    mandate_id: str = Field(..., min_length=1)
    operation: McpOperation = Field(
        default=McpOperation.CREATE_ORDER,
        description="The MCP operation requested (default: create_order).",
    )
    items: list[CartItemProposal] = Field(..., min_length=1)
    tax_paise: int = Field(default=0, ge=0)
    shipping_paise: int = Field(default=0, ge=0)
    total_paise: int = Field(..., ge=0)
    currency: Currency = Field(default=Currency.INR)
    idempotency_key: str = Field(..., min_length=1)


class StepUpDiff(BaseModel):
    """Step-up diff displayed in the UI (Section 16, PROJECT_CONTEXT.md)."""

    approved_paise: int
    proposed_paise: int
    delta_paise: int
    delta_percent: float
    reason: str


class DecisionTraceResponse(BaseModel):
    """Machine-readable decision trace explaining why a transaction was allowed or rejected."""

    decision: PolicyDecision
    checks_passed: list[str]
    checks_failed: list[str]
    rejection_reason: RejectionReason | None = None
    step_up_diff: StepUpDiff | None = None


class TransactionResponse(BaseModel):
    """Full transaction state response."""

    transaction_id: str
    buyer_id: str
    merchant_id: str
    mandate_id: str
    mandate_version: int
    policy_version: int
    cart_id: str | None = None
    cart_hash: str | None = None
    amount_paise: int
    currency: Currency
    state: TransactionState
    decision_trace: DecisionTraceResponse | None = None
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    idempotency_key: str
    nonce: str | None = None
    created_at: datetime
    updated_at: datetime


class StepUpApproveRequest(BaseModel):
    """Payload to approve a STEP_UP_REQUIRED transaction."""

    buyer_id: str = Field(..., min_length=1, description="Must match mandate buyer_id.")
    transaction_id: str = Field(..., min_length=1)
    approved_amount_paise: int = Field(..., ge=0)


class StepUpRejectRequest(BaseModel):
    """Payload to reject a STEP_UP_REQUIRED transaction."""

    buyer_id: str = Field(..., min_length=1)
    reason: str = Field(default="Rejected by buyer during step-up review.")
