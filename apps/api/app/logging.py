"""
Mandate Gateway — Structured Logging & Event Taxonomy Foundation
Section S00.5 — Observability Foundation
"""

import json
import logging
import time
from typing import Any, Dict

from apps.api.app.context import get_request_context
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


def redact_value(obj: Any) -> Any:
    """Recursively redacts SecretString objects inside strings, dicts, lists, and tuples."""
    if isinstance(obj, SecretString):
        return "[REDACTED]"
    elif isinstance(obj, str):
        if "SecretString(" in obj:
            return "[REDACTED]"
        return obj
    elif isinstance(obj, dict):
        return {k: redact_value(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [redact_value(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(redact_value(item) for item in obj)
    return obj


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
    Includes timestamp, level, service, environment, event, request_id, correlation_id, trace_id, and duration_ms.
    Guarantees log injection protection and secret redaction.
    """

    def __init__(
        self, service_name: str = "mandate-gateway", environment: str = "development"
    ) -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        ctx = get_request_context()

        req_id = getattr(record, "request_id", None) or ctx.get("request_id")
        corr_id = getattr(record, "correlation_id", None) or ctx.get("correlation_id")
        trace_id = getattr(record, "trace_id", None) or ctx.get("trace_id")

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
        }

        # Optional observability fields
        for field in (
            "duration_ms",
            "method",
            "path",
            "status_code",
            "error_type",
            "error_code",
        ):
            val = getattr(record, field, None)
            if val is not None:
                log_entry[field] = sanitize_log_string(str(val)) if isinstance(val, str) else val

        # Redact any accidental secret strings in log entry
        if isinstance(log_entry["event"], SecretString) or "SecretString(" in str(
            log_entry["event"]
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
