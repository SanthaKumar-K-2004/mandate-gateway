"""
Mandate Gateway — Configuration Types & Errors
Section S00.3 — Configuration & Secrets Management
"""

from __future__ import annotations

import enum
from typing import Any, Optional, Union


class Environment(str, enum.Enum):
    """Supported application execution environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"

    @classmethod
    def from_str(cls, value: str) -> "Environment":
        val_lower = str(value).strip().lower()
        for member in cls:
            if member.value == val_lower:
                return member
        valid_options = [m.value for m in cls]
        raise ConfigurationError(f"Invalid APP_ENV: '{value}'. Must be one of {valid_options}")


class LogLevel(str, enum.Enum):
    """Supported logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_str(cls, value: str) -> "LogLevel":
        val_upper = str(value).strip().upper()
        for member in cls:
            if member.value == val_upper:
                return member
        valid_options = [m.value for m in cls]
        raise ConfigurationError(f"Invalid LOG_LEVEL: '{value}'. Must be one of {valid_options}")


class ConfigurationError(ValueError):
    """Raised when configuration validation fails."""

    pass


class SecretString:
    """
    Wrapper for sensitive strings (passwords, tokens, API keys).
    Redacts content in str(), repr(), logs, and exception tracebacks to prevent secret leakage.
    """

    def __init__(self, secret_value: Optional[Union[str, SecretString]] = None):
        if secret_value is None:
            self._value: str = ""
        elif isinstance(secret_value, SecretString):
            self._value = secret_value.get_secret_value()
        else:
            self._value = str(secret_value)

    def get_secret_value(self) -> str:
        """Returns the raw unredacted secret value for secure internal usage."""
        return self._value

    def __repr__(self) -> str:
        return "SecretString('[REDACTED]')"

    def __str__(self) -> str:
        return "[REDACTED]"

    def __bool__(self) -> bool:
        return bool(self._value and self._value.strip())

    def __len__(self) -> int:
        return len(self._value)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SecretString):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return False
