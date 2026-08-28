"""
S02.8 — Decision Trace & Explainability API Response Contracts.

Response schemas for `/api/transactions/{id}/explain` endpoint (Section 28, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from pydantic import BaseModel

from apps.api.domain.types import PolicyDecision


class ExplainabilityCheckStepResponse(BaseModel):
    """Response DTO for an individual security check step in a decision trace."""

    control_name: str
    passed: bool
    decision: PolicyDecision
    rejection_reason: str | None = None
    detail: str | None = None
    evaluated_at: str


class ExplainabilityReportResponse(BaseModel):
    """Response DTO for transaction explainability report."""

    transaction_id: str
    mandate_id: str | None = None
    merchant_id: str | None = None
    buyer_id: str | None = None
    overall_decision: PolicyDecision
    summary_reason: str
    control_steps: list[ExplainabilityCheckStepResponse]
    razorpay_execution_status: str
    audit_event_id: str | None = None
    action_receipt_id: str | None = None
    formatted_text_trace: str
