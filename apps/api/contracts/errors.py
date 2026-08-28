"""
S01.1 — Structured API Error Contracts.

Standardized gateway error response body (RFC 7807-compatible style).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.api.domain.types import RejectionReason


class GatewayErrorResponse(BaseModel):
    """
    Standard error body returned by all Mandate Gateway endpoints.

    Always includes a machine-readable code, human-readable message,
    and request/correlation IDs for debugging.
    """

    code: str = Field(..., description="Machine-readable error code.")
    message: str = Field(..., description="Human-readable explanation.")
    rejection_reason: RejectionReason | None = Field(
        default=None,
        description="Populated when error is a PolicyEngine REJECT decision.",
    )
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = Field(default=None)
    timestamp: str = Field(...)
