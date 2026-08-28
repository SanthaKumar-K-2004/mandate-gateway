"""
S02.8 — Decision Trace & Explainability Data Contracts.

Data types for structured transaction decision traces (Section 22, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from apps.api.domain.types import PolicyDecision, RejectionReason


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True, slots=True)
class CheckTraceStep:
    """Individual security control evaluation step in a decision trace."""

    control_name: str
    passed: bool
    decision: PolicyDecision
    rejection_reason: RejectionReason | None = None
    detail: str | None = None
    evaluated_at: datetime = field(default_factory=_utc_now)


class DecisionTraceReport(BaseModel):
    """
    Complete explainability report for a transaction authorization & execution lifecycle.
    """

    model_config = {"frozen": True}

    transaction_id: str = Field(..., min_length=1)
    mandate_id: str | None = None
    merchant_id: str | None = None
    buyer_id: str | None = None
    overall_decision: PolicyDecision
    summary_reason: str
    control_steps: list[dict[str, Any]]
    razorpay_execution_status: str
    audit_event_id: str | None = None
    action_receipt_id: str | None = None
    formatted_text_trace: str
