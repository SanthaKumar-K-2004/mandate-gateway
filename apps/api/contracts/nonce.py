"""
API contracts for S01.9 Nonce & Authorization Freshness Engine.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from apps.api.domain.types import NonceState, PolicyDecision, RejectionReason


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class NonceIssueRequest(BaseModel):
    """Request contract for issuing a new authorization nonce."""

    mandate_id: str = Field(
        ..., min_length=1, description="Target mandate ID for identity binding."
    )
    transaction_id: str = Field(..., min_length=1, description="Target transaction/action ID.")
    ttl_seconds: int = Field(
        default=300, ge=1, description="Nonce validity lifetime in seconds (default 300s/5min)."
    )


class NonceIssueResponse(BaseModel):
    """Response contract after issuing a new authorization nonce."""

    nonce_id: str = Field(..., description="Unique nonce record identifier.")
    nonce_value: str = Field(
        ..., min_length=16, description="Cryptographically random 32-hex nonce string."
    )
    mandate_id: str = Field(..., description="Bound mandate ID.")
    transaction_id: str = Field(..., description="Bound transaction ID.")
    state: NonceState = Field(default=NonceState.ISSUED)
    issued_at: datetime = Field(default_factory=_utc_now)
    expires_at: datetime = Field(..., description="UTC expiration time.")


class NonceConsumeRequest(BaseModel):
    """Request contract for validating and consuming an authorization nonce."""

    nonce_value: str = Field(
        ..., min_length=1, description="The nonce string to validate and consume."
    )
    mandate_id: str = Field(..., min_length=1, description="Expected bound mandate ID.")
    transaction_id: str = Field(..., min_length=1, description="Expected bound transaction ID.")


class NonceConsumeResponse(BaseModel):
    """Response contract after nonce evaluation and consumption attempt."""

    valid: bool = Field(..., description="True if nonce was valid and successfully consumed.")
    decision: PolicyDecision = Field(
        ..., description="ALLOW if valid, REJECT if invalid/expired/consumed."
    )
    nonce_value: str = Field(..., description="Target nonce string.")
    mandate_id: str = Field(..., description="Target mandate ID.")
    transaction_id: str = Field(..., description="Target transaction ID.")
    state: NonceState = Field(..., description="Current state of the nonce (ISSUED or CONSUMED).")
    rejection_reason: RejectionReason | None = Field(
        default=None, description="Reason if validation failed."
    )
    rejection_detail: str | None = Field(
        default=None, description="Detailed explanation if validation failed."
    )
    evaluated_at: datetime = Field(default_factory=_utc_now)
