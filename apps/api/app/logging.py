"""
Mandate Gateway — Structured Logging & Event Taxonomy Foundation
Section S00.5 — Observability Foundation
"""

import json
import logging
import re
import time
from typing import Any, Dict

from apps.api.config.types import SecretString

# Machine-Readable Event Taxonomy
EVENT_APPLICATION_STARTED = "application.started"
EVENT_APPLICATION_READY = "application.ready"
EVENT_APPLICATION_SHUTDOWN = "application.shutdown"
EVENT_REQUEST_STARTED = "request.started"
EVENT_REQUEST_COMPLETED = "request.completed"
EVENT_REQUEST_FAILED = "request.failed"
EVENT_DEPENDENCY_FAILED = "dependency.failed"
EVENT_CONFIGURATION_FAILED = "configuration.failed"


def sanitize_log_string(val: Any) -> str:
    """Sanitizes control characters, newlines, and carriage returns to prevent log injection."""
    if not isinstance(val, str):
        return str(val)
    # Replace control characters / newlines to preserve single-line JSON formatting
    return val.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")


SENSITIVE_KEY_PATTERNS = {
    "secret",
    "password",
    "token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "private_key",
    "signature",
    "cvv",
    "nonce",
    "credential",
}

_SENSITIVE_STRING_PATTERN = re.compile(
    r"(?i)\b(secret(?:_key)?|password|token|api_key|apikey|auth(?:orization)?"
    r"|private_key|signature|cvv|nonce|credential)\s*=\s*([^\s,;]+)"
)


def redact_value(obj: Any) -> Any:
    """Recursively redacts SecretString objects and sensitive keys inside strings, dicts, lists, and tuples."""
    if isinstance(obj, SecretString):
        return "[REDACTED]"
    elif isinstance(obj, str):
        if "SecretString(" in obj:
            return "[REDACTED]"
        return _SENSITIVE_STRING_PATTERN.sub(r"\1=[REDACTED]", obj)
    elif isinstance(obj, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in obj.items():
            key_lower = str(k).lower()
            if any(pattern in key_lower for pattern in SENSITIVE_KEY_PATTERNS):
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_value(v)
        return cleaned
    elif isinstance(obj, list):
        return [redact_value(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(redact_value(item) for item in obj)
    return obj


# Alias for backwards compatibility and test clarity
redact_sensitive_data = redact_value


class SecretRedactionFilter(logging.Filter):
    """Logging filter that redacts SecretString instances or sensitive text patterns."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_value(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = redact_value(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(redact_value(arg) for arg in record.args)
        return True


class StructuredJsonFormatter(logging.Formatter):
    """
    Structured JSON log formatter for Mandate Gateway.
    Includes timestamp, level, service, environment, event, request_id, correlation_id, trace_id,
    span_id, merchant_id, buyer_id, transaction_id, mandate_id, idempotency_key, execution_attempt_id,
    outbox_event_id, provider_reference, operation, status, error_code, latency_ms.
    Guarantees log injection protection and secret redaction.
    """

    def __init__(
        self, service_name: str = "mandate-gateway", environment: str = "development"
    ) -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        from apps.api.app.context import get_full_context

        ctx = get_full_context()

        req_id = getattr(record, "request_id", None) or ctx.get("request_id")
        corr_id = getattr(record, "correlation_id", None) or ctx.get("correlation_id")
        trace_id = getattr(record, "trace_id", None) or ctx.get("trace_id")
        span_id = getattr(record, "span_id", None) or ctx.get("span_id")

        raw_event = record.getMessage()
        sanitized_event = sanitize_log_string(raw_event)

        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt)
            or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "service": self.service_name,
            "environment": self.environment,
            "event": sanitized_event,
            "logger": record.name,
            "request_id": req_id,
            "correlation_id": corr_id,
            "trace_id": trace_id,
            "span_id": span_id,
        }

        # Context-derived domain identity & operational fields
        for ctx_key in (
            "transaction_id",
            "merchant_id",
            "buyer_id",
            "mandate_id",
            "idempotency_key",
            "execution_attempt_id",
            "audit_event_id",
            "receipt_id",
            "webhook_event_id",
            "outbox_event_id",
            "worker_id",
            "provider_reference",
            "operation",
            "status",
            "error_code",
            "latency_ms",
        ):
            val = getattr(record, ctx_key, None)
            if val is None:
                val = ctx.get(ctx_key)
            if val is not None:
                log_entry[ctx_key] = sanitize_log_string(str(val)) if isinstance(val, str) else val

        # Optional operational observability fields
        for field in (
            "duration_ms",
            "method",
            "path",
            "status_code",
            "error_type",
            "operation_name",
            "error_category",
        ):
            val = getattr(record, field, None)
            if val is not None:
                log_entry[field] = sanitize_log_string(str(val)) if isinstance(val, str) else val

        # Redact any accidental secret strings or sensitive patterns in log entry
        log_entry = redact_value(log_entry)
        if isinstance(log_entry.get("event"), SecretString) or "SecretString(" in str(
            log_entry.get("event")
        ):
            log_entry["event"] = "[REDACTED]"

        return json.dumps(log_entry)


def setup_logging(
    service_name: str = "mandate-gateway",
    environment: str = "development",
    log_level: str = "INFO",
) -> logging.Logger:
    """Configures structured logging foundation for the application runtime."""
    logger = logging.getLogger("mandate_gateway")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(
        StructuredJsonFormatter(service_name=service_name, environment=environment)
    )
    handler.addFilter(SecretRedactionFilter())

    logger.addHandler(handler)
    return logger
