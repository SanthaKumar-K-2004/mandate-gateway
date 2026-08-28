"""
S01.6 — Cart Integrity Verification API Contracts.

Request & Response DTO schemas for cart integrity verification endpoints.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from apps.api.domain.types import RejectionReason


class CartIntegrityVerifyRequest(BaseModel):
    """Request payload to verify cart integrity."""

    authorized_cart_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Trusted 64-character SHA-256 canonical cart hash digest.",
    )
    cart_id: str = Field(..., min_length=1)
    current_cart_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Current cart digest to verify.",
    )


class CartIntegrityVerifyResponse(BaseModel):
    """Response payload returned by Cart Integrity Verification."""

    valid: bool
    authorized_hash: str
    current_hash: str
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    field_mismatches: list[str]
    evaluated_at: datetime
