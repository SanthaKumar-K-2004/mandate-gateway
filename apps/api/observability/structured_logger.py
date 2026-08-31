"""
Mandate Gateway — Structured Production Logging & Secret Redaction (M29)
Workstream 5 — Formats log events in structured JSON and automatically redacts API keys,
passwords, bearer tokens, HMAC secrets, and credit card numbers.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict

SENSITIVE_KEY_PATTERNS = [
    re.compile(r"api_?key", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"auth(orization)?", re.IGNORECASE),
    re.compile(r"card_?number", re.IGNORECASE),
    re.compile(r"cvv", re.IGNORECASE),
    re.compile(r"hmac", re.IGNORECASE),
]

SENSITIVE_VALUE_REGEXES = [
    re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE),
    re.compile(r"\b[456]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),  # Credit cards
    re.compile(r"([a-zA-Z0-9_-]{32,})"),  # Long token/key heuristics in secret context
]


class SecretRedactor:
    """Utility to sanitize dictionaries and strings against credential exposure."""

    REDACTED_TEXT = "[REDACTED]"

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact sensitive keys in dictionaries."""
        clean: Dict[str, Any] = {}
        for key, val in data.items():
            if any(pat.search(key) for pat in SENSITIVE_KEY_PATTERNS):
                clean[key] = cls.REDACTED_TEXT
            elif isinstance(val, dict):
                clean[key] = cls.sanitize_dict(val)
            elif isinstance(val, str):
                clean[key] = cls.sanitize_string(val)
            else:
                clean[key] = val
        return clean

    @classmethod
    def sanitize_string(cls, text: str) -> str:
        """Redact bearer tokens and credit card numbers in free text."""
        sanitized = text
        for rx in SENSITIVE_VALUE_REGEXES:
            sanitized = rx.sub(cls.REDACTED_TEXT, sanitized)
        return sanitized


class StructuredJSONFormatter(logging.Formatter):
    """Production JSON log formatter with mandatory audit fields and secret redaction."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": SecretRedactor.sanitize_string(record.getMessage()),
            "request_id": getattr(record, "request_id", None),
            "correlation_id": getattr(record, "correlation_id", None),
            "operation_type": getattr(record, "operation_type", "GENERIC_OPERATION"),
            "connector_id": getattr(record, "connector_id", None),
            "outcome": getattr(record, "outcome", "SUCCESS"),
        }

        # Redact extra fields if provided
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_obj["extra_data"] = SecretRedactor.sanitize_dict(record.extra_data)

        return json.dumps(log_obj)
