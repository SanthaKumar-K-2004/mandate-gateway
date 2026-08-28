"""
S03.3 — Security Hardening Agent Interface.

Agent-facing SecurityHardeningManager exposing posture monitoring, rate-limiting,
and offline verification (Section 34 & 35, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from typing import Any

from agent.security.types import (
    RateLimitRequest,
    RateLimitResponse,
    ReceiptVerifyRequest,
    ReceiptVerifyResponse,
    SecurityPostureStatus,
)
from apps.api.domain.security_hardening import SecurityHardeningEngine


class SecurityHardeningManager:
    """Agent interface for security posture monitoring and offline receipt verification."""

    def __init__(self) -> None:
        self.engine = SecurityHardeningEngine()

    def get_posture(self) -> SecurityPostureStatus:
        """Get system-wide security posture and fail-closed health status."""
        return self.engine.get_posture()

    def check_rate_limit(self, req: RateLimitRequest) -> RateLimitResponse:
        """Evaluate rate-limiting for a given request."""
        return self.engine.check_rate_limit(req)

    def redact_sensitive_data(self, data: Any) -> Any:
        """Redact sensitive keys/tokens from a payload."""
        return self.engine.redact_sensitive_data(data)

    def verify_receipt(self, req: ReceiptVerifyRequest) -> ReceiptVerifyResponse:
        """Cryptographically verify an action receipt offline."""
        return self.engine.verify_receipt_cryptographic_offline(req)
