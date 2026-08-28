"""
S03.3 — Security Hardening DTOs & Contracts.

Defines request/response contracts for security posture status, rate limiting, and receipt verification (Section 34 & 35, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class SecurityPostureStatus(BaseModel):
    """System-wide security posture and fail-closed operational health status."""

    fail_closed_mode_active: bool = True
    database_persistence_healthy: bool = True
    redis_cache_healthy: bool = True
    rate_limiter_active: bool = True
    secret_redactor_active: bool = True
    active_threat_mitigations: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=_utc_now)


class RateLimitRequest(BaseModel):
    """Request payload for checking rate limits."""

    identifier: str = Field(..., min_length=1, description="IP, buyer_id, or merchant_id")
    action: str = Field(default="execute_intent", description="Action being rate limited")
    max_requests: int = Field(default=100, ge=1)
    window_seconds: int = Field(default=60, ge=1)


class RateLimitResponse(BaseModel):
    """Response payload for rate limit evaluations."""

    allowed: bool
    identifier: str
    current_count: int
    max_requests: int
    window_seconds: int
    retry_after_seconds: float = 0.0
    evaluated_at: datetime = Field(default_factory=_utc_now)


class ReceiptVerifyRequest(BaseModel):
    """Request payload for offline cryptographic receipt verification."""

    receipt_id: str = Field(..., min_length=1)
    transaction_id: str = Field(..., min_length=1)
    mandate_id: str = Field(..., min_length=1)
    merchant_id: str = Field(..., min_length=1)
    policy_version: int = Field(..., ge=1)
    cart_hash: str = Field(..., min_length=1)
    amount_paise: int = Field(..., ge=0)
    currency: str = Field(default="INR")
    decision: str = Field(..., min_length=1)
    execution_tool: str = Field(..., min_length=1)
    execution_reference: str = Field(..., min_length=1)
    audit_hash: str = Field(..., min_length=1)
    signature: str = Field(..., min_length=1)


class ReceiptVerifyResponse(BaseModel):
    """Outcome of offline cryptographic receipt verification."""

    valid: bool
    receipt_id: str
    signature_valid: bool
    payload_hash_valid: bool
    audit_chain_valid: bool
    rejection_detail: str | None = None
    verified_at: datetime = Field(default_factory=_utc_now)
