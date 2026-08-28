"""
API contracts for S01.10 Step-Up / Human-in-the-Loop Authorization Engine.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from apps.api.contracts.transaction import StepUpDiff
from apps.api.domain.types import PolicyDecision, RejectionReason, StepUpZone


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class StepUpChallengeCreateRequest(BaseModel):
    """Request contract for creating a step-up approval challenge."""

    mandate_id: str = Field(..., min_length=1, description="Target mandate ID.")
    transaction_id: str = Field(..., min_length=1, description="Target transaction ID.")
    cart_hash: str = Field(..., min_length=1, description="Canonical cart SHA-256 digest.")
    approved_paise: int = Field(..., ge=0, description="Originally approved mandate cap in paise.")
    proposed_paise: int = Field(..., ge=0, description="Proposed total cart amount in paise.")
    merchant_id: str = Field(..., min_length=1, description="Target merchant ID.")
    ttl_seconds: int = Field(
        default=300, ge=1, description="Challenge lifetime in seconds (default 300s)."
    )


class StepUpChallengeCreateResponse(BaseModel):
    """Response contract after creating a step-up challenge."""

    challenge_id: str = Field(..., description="Unique challenge ID.")
    mandate_id: str = Field(..., description="Bound mandate ID.")
    transaction_id: str = Field(..., description="Bound transaction ID.")
    cart_hash: str = Field(..., description="Bound cart hash.")
    merchant_id: str = Field(..., description="Bound merchant ID.")
    approved_paise: int = Field(..., ge=0)
    proposed_paise: int = Field(..., ge=0)
    status: str = Field(default="PENDING")
    created_at: datetime = Field(default_factory=_utc_now)
    expires_at: datetime = Field(..., description="Expiration timestamp.")


class StepUpConfirmRequest(BaseModel):
    """Request contract for recording a human approval/confirmation."""

    challenge_id: str = Field(..., min_length=1, description="Target step-up challenge ID.")
    mandate_id: str = Field(..., min_length=1, description="Expected mandate ID.")
    transaction_id: str = Field(..., min_length=1, description="Expected transaction ID.")
    cart_hash: str = Field(..., min_length=1, description="Expected cart hash.")
    proposed_paise: int = Field(..., ge=0, description="Expected proposed amount in paise.")
    merchant_id: str = Field(..., min_length=1, description="Expected merchant ID.")
    confirmed_by: str = Field(
        ..., min_length=1, description="Human/Buyer identity confirming the step-up."
    )


class StepUpConfirmResponse(BaseModel):
    """Response contract after recording a human confirmation attempt."""

    success: bool = Field(..., description="True if confirmation was recorded and approved.")
    challenge_id: str = Field(..., description="Target challenge ID.")
    status: str = Field(
        ..., description="Current status of the challenge (APPROVED, REJECTED, EXPIRED)."
    )
    message: str = Field(..., description="Human-readable outcome summary.")
    confirmed_at: datetime | None = Field(default=None)


class StepUpValidateResponse(BaseModel):
    """Response contract after evaluating step-up confirmation for authorization."""

    valid: bool = Field(..., description="True if step-up approval is valid and allows execution.")
    decision: PolicyDecision = Field(..., description="ALLOW, STEP_UP_REQUIRED, or REJECT.")
    zone: StepUpZone = Field(
        ..., description="Evaluated StepUpZone (AUTO_EXECUTE, STEP_UP_REQUIRED, HARD_REJECT)."
    )
    challenge_id: str | None = Field(default=None)
    step_up_diff: StepUpDiff | None = Field(default=None)
    rejection_reason: RejectionReason | None = Field(default=None)
    rejection_detail: str | None = Field(default=None)
    evaluated_at: datetime = Field(default_factory=_utc_now)
