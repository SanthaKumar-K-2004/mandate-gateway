"""
S03.3 — Security Hardening REST API Router.

Implements REST API endpoints for security posture observability, rate-limiting evaluations,
and offline cryptographic receipt verification (Section 34 & Section 35, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from typing import Any

from agent.security.errors import HardeningError
from agent.security.types import (
    RateLimitRequest,
    RateLimitResponse,
    ReceiptVerifyRequest,
    ReceiptVerifyResponse,
    SecurityPostureStatus,
)
from apps.api.domain.security_hardening import SecurityHardeningEngine

_SECURITY_ENGINE = SecurityHardeningEngine()


def _get_security_engine() -> SecurityHardeningEngine:
    return _SECURITY_ENGINE


try:
    from fastapi import APIRouter, HTTPException, status

    security_router = APIRouter(prefix="/api/security", tags=["security-hardening"])

    @security_router.get(
        "/hardening/status",
        response_model=SecurityPostureStatus,
        summary="Fetch system security posture and fail-closed operational health.",
    )
    def get_security_posture_endpoint() -> SecurityPostureStatus:
        engine = _get_security_engine()
        return engine.get_posture()

    @security_router.post(
        "/rate-limit/check",
        response_model=RateLimitResponse,
        summary="Evaluate sliding window rate limit for an identifier.",
    )
    def check_rate_limit_endpoint(req: RateLimitRequest) -> RateLimitResponse:
        engine = _get_security_engine()
        try:
            return engine.check_rate_limit(req)
        except HardeningError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=e.message,
            )

    @security_router.post(
        "/verify-receipt",
        response_model=ReceiptVerifyResponse,
        summary="Cryptographically verify an Ed25519 signed action receipt offline.",
    )
    def verify_receipt_endpoint(req: ReceiptVerifyRequest) -> ReceiptVerifyResponse:
        engine = _get_security_engine()
        try:
            return engine.verify_receipt_cryptographic_offline(req)
        except HardeningError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=e.message,
            )

except ImportError:  # pragma: no cover
    security_router: Any = None  # type: ignore[no-redef]
