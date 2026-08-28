"""
API contracts for S01.8 Replay Protection Engine.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from apps.api.domain.types import PolicyDecision, RejectionReason


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ReplayCheckRequest(BaseModel):
    """Request contract for checking and recording a replay fingerprint."""

    mandate_id: str = Field(..., min_length=1, description="Mandate ID for transaction identity.")
    transaction_id: str = Field(..., min_length=1, description="Unique transaction/action ID.")
    cart_hash: str | None = Field(
        default=None, description="Optional canonical cart SHA-256 digest."
    )
    merchant_id: str | None = Field(default=None, description="Optional merchant ID.")
    ttl_seconds: int = Field(
        default=86400,
        ge=1,
        description="Time to live for replay record in seconds (default 24 hours).",
    )


class ReplayCheckResponse(BaseModel):
    """Response contract for replay protection evaluation."""

    valid: bool = Field(
        ..., description="True if transaction is new (first use). False if replayed."
    )
    decision: PolicyDecision = Field(..., description="ALLOW if new, REJECT if replayed.")
    fingerprint: str = Field(..., description="Canonical replay SHA-256 fingerprint digest.")
    mandate_id: str = Field(..., description="Target mandate ID.")
    transaction_id: str = Field(..., description="Target transaction ID.")
    rejection_reason: RejectionReason | None = Field(
        default=None, description="REPLAY_ATTEMPT_DETECTED if replayed."
    )
    rejection_detail: str | None = Field(
        default=None, description="Detailed explanation if replayed."
    )
    evaluated_at: datetime = Field(default_factory=_utc_now)
