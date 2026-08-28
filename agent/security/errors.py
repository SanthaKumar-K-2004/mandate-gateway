"""
S03.3 — Security Hardening Error Taxonomy.

Defines error codes and structured exceptions for security hardening & fail-closed audit (Section 35, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class HardeningErrorCode(str, Enum):
    """Enumeration of security hardening failure modes."""

    DATABASE_FAIL_CLOSED = "DATABASE_FAIL_CLOSED"
    EPHEMERAL_CACHE_UNAVAILABLE = "EPHEMERAL_CACHE_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    UNSAFE_NETWORK_BINDING = "UNSAFE_NETWORK_BINDING"
    SECRET_LEAKAGE_DETECTED = "SECRET_LEAKAGE_DETECTED"
    REPLAY_SIGNATURE_INVALID = "REPLAY_SIGNATURE_INVALID"
    RECEIPT_VERIFICATION_FAILED = "RECEIPT_VERIFICATION_FAILED"
    FAIL_CLOSED_SYSTEM_ERROR = "FAIL_CLOSED_SYSTEM_ERROR"


class HardeningError(Exception):
    """Exception raised during security hardening and fail-closed audit operations."""

    def __init__(
        self,
        code: HardeningErrorCode,
        message: str,
        detail: str | None = None,
    ) -> None:
        super().__init__(f"[{code.value}] {message}")
        self.code = code
        self.message = message
        self.detail = detail
