"""
Razerpay Python SDK — Custom Exceptions
"""

from __future__ import annotations


class RazerpayError(Exception):
    """Base exception for all Razerpay SDK errors."""

    def __init__(
        self, message: str, code: str = "SDK_ERROR", request_id: str | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.request_id = request_id

    def __str__(self) -> str:
        req_str = f" [request_id={self.request_id}]" if self.request_id else ""
        return f"[{self.code}] {self.message}{req_str}"


class AuthenticationError(RazerpayError):
    """Raised when authentication credentials fail (HTTP 401)."""

    def __init__(
        self, message: str = "Invalid API key or credentials.", request_id: str | None = None
    ) -> None:
        super().__init__(message, code="UNAUTHORIZED", request_id=request_id)


class IdempotencyError(RazerpayError):
    """Raised when idempotency key conflicts occur (HTTP 409)."""

    def __init__(
        self, message: str = "Idempotency key payload mismatch.", request_id: str | None = None
    ) -> None:
        super().__init__(message, code="IDEMPOTENCY_CONFLICT", request_id=request_id)


class ValidationError(RazerpayError):
    """Raised when request validation fails (HTTP 400)."""

    def __init__(
        self, message: str = "Invalid request payload.", request_id: str | None = None
    ) -> None:
        super().__init__(message, code="INVALID_REQUEST", request_id=request_id)


class APIError(RazerpayError):
    """Raised when backend API returns unexpected HTTP error."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: str = "API_ERROR",
        request_id: str | None = None,
    ) -> None:
        super().__init__(message, code=code, request_id=request_id)
        self.status_code = status_code
