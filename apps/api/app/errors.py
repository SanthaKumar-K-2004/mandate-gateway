"""
Mandate Gateway — Foundational Runtime Error Hierarchy
Section S00.4 — Application Runtime Foundation
"""

from typing import Any, Dict, Optional, Tuple

from apps.api.config.types import Environment, SecretString


class RuntimeErrorBase(Exception):
    """Base exception for all Mandate Gateway runtime errors."""

    def __init__(
        self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR"
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

    def to_dict(self, environment: Optional[Environment] = None) -> Dict[str, Any]:
        """Formats safe error payload preventing secret or traceback leakage."""
        from apps.api.app.context import get_request_context

        ctx = get_request_context()
        corr_id = ctx.get("correlation_id") or ctx.get("request_id")

        res: Dict[str, Any] = {
            "error": {
                "code": self.error_code,
                "message": self._redact_string(self.message),
            }
        }
        if corr_id:
            res["error"]["correlation_id"] = corr_id
        return res

    @staticmethod
    def _redact_string(text: str) -> str:
        if isinstance(text, SecretString):
            return "[REDACTED]"
        if "SecretString(" in str(text):
            return "[REDACTED]"
        return str(text)


class ConfigurationError(RuntimeErrorBase):
    """Raised when configuration validation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500, error_code="CONFIGURATION_ERROR")


class RuntimeInitializationError(RuntimeErrorBase):
    """Raised when application startup initialization fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500, error_code="RUNTIME_INITIALIZATION_ERROR")


class DependencyInitializationError(RuntimeErrorBase):
    """Raised when dependency setup fails during startup."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500, error_code="DEPENDENCY_INITIALIZATION_ERROR")


class RequestValidationError(RuntimeErrorBase):
    """Raised when request identity or parameters are malformed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400, error_code="REQUEST_VALIDATION_ERROR")


class InternalApplicationError(RuntimeErrorBase):
    """Raised for unexpected internal server errors."""

    def __init__(self, message: str = "An internal application error occurred.") -> None:
        super().__init__(message, status_code=500, error_code="INTERNAL_SERVER_ERROR")


class AuthorizationError(RuntimeErrorBase):
    """Raised when request authorization fails."""

    def __init__(self, message: str = "Authorization denied.") -> None:
        super().__init__(message, status_code=403, error_code="AUTHORIZATION_DENIED")


class MandateError(RuntimeErrorBase):
    """Raised when mandate rules or validation fail."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400, error_code="MANDATE_ERROR")


class BudgetExceededError(RuntimeErrorBase):
    """Raised when budget limits are exceeded."""

    def __init__(self, message: str = "Budget limit exceeded.") -> None:
        super().__init__(message, status_code=422, error_code="BUDGET_EXCEEDED")


class StepUpRequiredError(RuntimeErrorBase):
    """Raised when step-up authentication challenge is required."""

    def __init__(self, message: str = "Step-up challenge required.") -> None:
        super().__init__(message, status_code=401, error_code="STEP_UP_REQUIRED")


class ReplayAttackError(RuntimeErrorBase):
    """Raised when a duplicate request/replay attack is detected."""

    def __init__(self, message: str = "Replay attack detected.") -> None:
        super().__init__(message, status_code=409, error_code="REPLAY_ATTACK_DETECTED")


class InvalidNonceError(RuntimeErrorBase):
    """Raised when a nonce is invalid, consumed, or expired."""

    def __init__(self, message: str = "Invalid or expired nonce.") -> None:
        super().__init__(message, status_code=400, error_code="INVALID_NONCE")


class ProviderTimeoutError(RuntimeErrorBase):
    """Raised when external provider times out or outcome is ambiguous."""

    def __init__(self, message: str = "Provider call timed out.") -> None:
        super().__init__(message, status_code=504, error_code="PROVIDER_TIMEOUT")


def format_exception_response(exc: Exception) -> Tuple[int, Dict[str, Any]]:
    """
    Centralized exception translation mapping any runtime exception to safe HTTP response.
    Never exposes stack traces or internal secrets to API clients.
    """
    if isinstance(exc, RuntimeErrorBase):
        return exc.status_code, exc.to_dict()

    internal_err = InternalApplicationError()
    return internal_err.status_code, internal_err.to_dict()
