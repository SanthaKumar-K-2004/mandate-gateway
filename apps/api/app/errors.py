"""
Mandate Gateway — Foundational Runtime Error Hierarchy
Section S00.4 — Application Runtime Foundation
"""

from typing import Any, Dict, Optional

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
        res: Dict[str, Any] = {
            "error": {
                "code": self.error_code,
                "message": self._redact_string(self.message),
            }
        }
        return res

    @staticmethod
    def _redact_string(text: str) -> str:
        if isinstance(text, SecretString):
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
