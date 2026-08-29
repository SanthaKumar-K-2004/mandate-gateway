"""
Mandate Gateway — Request & Observability Context Foundation
Section S00.5, M08 & M15 — Deep Observability & Multi-Task Correlation Isolation
"""

from __future__ import annotations

import contextvars
import re
from typing import Any, Dict, Optional
import uuid

# ContextVars for async-safe request correlation propagation
_REQUEST_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)
_CORRELATION_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)
_TRACE_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)
_SPAN_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "span_id", default=None
)

# ContextVars for domain transaction & forensic identity propagation
_TRANSACTION_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "transaction_id", default=None
)
_MERCHANT_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "merchant_id", default=None
)
_BUYER_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "buyer_id", default=None
)
_MANDATE_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "mandate_id", default=None
)
_IDEMPOTENCY_KEY_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "idempotency_key", default=None
)
_EXECUTION_ATTEMPT_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "execution_attempt_id", default=None
)
_AUDIT_EVENT_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "audit_event_id", default=None
)
_RECEIPT_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "receipt_id", default=None
)
_WEBHOOK_EVENT_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "webhook_event_id", default=None
)
_OUTBOX_EVENT_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "outbox_event_id", default=None
)
_WORKER_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "worker_id", default=None
)
_PROVIDER_REFERENCE_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "provider_reference", default=None
)
_OPERATION_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "operation", default=None
)
_EVENT_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("event", default=None)
_STATUS_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("status", default=None)
_ERROR_CODE_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "error_code", default=None
)
_LATENCY_MS_VAR: contextvars.ContextVar[Optional[float]] = contextvars.ContextVar(
    "latency_ms", default=None
)

_VALID_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]{1,128}$")


def validate_and_sanitize_request_id(request_id_raw: Optional[str]) -> str:
    """
    Validates and sanitizes incoming request identifier.
    If valid, returns stripped request ID.
    If invalid, malformed, contains injection payloads, or exceeds 128 chars,
    returns a newly generated UUIDv4 request ID.
    """
    if not request_id_raw or not isinstance(request_id_raw, str):
        return f"req_{uuid.uuid4().hex}"
    clean = request_id_raw.strip()
    if len(clean) > 128 or not _VALID_ID_PATTERN.match(clean):
        return f"req_{uuid.uuid4().hex}"
    return clean


def set_request_context(
    request_id: str,
    correlation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
) -> None:
    """Sets current async request context identifiers with safe validation."""
    clean_req = validate_and_sanitize_request_id(request_id)
    clean_corr = validate_and_sanitize_request_id(correlation_id) if correlation_id else clean_req
    clean_trace = validate_and_sanitize_request_id(trace_id) if trace_id else clean_corr

    _REQUEST_ID_VAR.set(clean_req)
    _CORRELATION_ID_VAR.set(clean_corr)
    _TRACE_ID_VAR.set(clean_trace)
    if span_id is not None:
        _SPAN_ID_VAR.set(span_id)


def set_transaction_context(
    transaction_id: Optional[str] = None,
    merchant_id: Optional[str] = None,
    buyer_id: Optional[str] = None,
    mandate_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    execution_attempt_id: Optional[str] = None,
    audit_event_id: Optional[str] = None,
    receipt_id: Optional[str] = None,
    webhook_event_id: Optional[str] = None,
    outbox_event_id: Optional[str] = None,
    worker_id: Optional[str] = None,
    provider_reference: Optional[str] = None,
    operation: Optional[str] = None,
    event: Optional[str] = None,
    status: Optional[str] = None,
    error_code: Optional[str] = None,
    latency_ms: Optional[float] = None,
) -> None:
    """Enriches async context with domain operation identifiers."""
    if transaction_id is not None:
        _TRANSACTION_ID_VAR.set(transaction_id)
    if merchant_id is not None:
        _MERCHANT_ID_VAR.set(merchant_id)
    if buyer_id is not None:
        _BUYER_ID_VAR.set(buyer_id)
    if mandate_id is not None:
        _MANDATE_ID_VAR.set(mandate_id)
    if idempotency_key is not None:
        _IDEMPOTENCY_KEY_VAR.set(idempotency_key)
    if execution_attempt_id is not None:
        _EXECUTION_ATTEMPT_ID_VAR.set(execution_attempt_id)
    if audit_event_id is not None:
        _AUDIT_EVENT_ID_VAR.set(audit_event_id)
    if receipt_id is not None:
        _RECEIPT_ID_VAR.set(receipt_id)
    if webhook_event_id is not None:
        _WEBHOOK_EVENT_ID_VAR.set(webhook_event_id)
    if outbox_event_id is not None:
        _OUTBOX_EVENT_ID_VAR.set(outbox_event_id)
    if worker_id is not None:
        _WORKER_ID_VAR.set(worker_id)
    if provider_reference is not None:
        _PROVIDER_REFERENCE_VAR.set(provider_reference)
    if operation is not None:
        _OPERATION_VAR.set(operation)
    if event is not None:
        _EVENT_VAR.set(event)
    if status is not None:
        _STATUS_VAR.set(status)
    if error_code is not None:
        _ERROR_CODE_VAR.set(error_code)
    if latency_ms is not None:
        _LATENCY_MS_VAR.set(latency_ms)


def get_request_context() -> Dict[str, Optional[str]]:
    """Returns a dictionary containing current request correlation identifiers."""
    return {
        "request_id": _REQUEST_ID_VAR.get(),
        "correlation_id": _CORRELATION_ID_VAR.get(),
        "trace_id": _TRACE_ID_VAR.get(),
        "span_id": _SPAN_ID_VAR.get(),
    }


def get_full_context() -> Dict[str, Any]:
    """Returns all request and domain operation context identifiers."""
    ctx: Dict[str, Any] = get_request_context()
    ctx.update(
        {
            "transaction_id": _TRANSACTION_ID_VAR.get(),
            "merchant_id": _MERCHANT_ID_VAR.get(),
            "buyer_id": _BUYER_ID_VAR.get(),
            "mandate_id": _MANDATE_ID_VAR.get(),
            "idempotency_key": _IDEMPOTENCY_KEY_VAR.get(),
            "execution_attempt_id": _EXECUTION_ATTEMPT_ID_VAR.get(),
            "audit_event_id": _AUDIT_EVENT_ID_VAR.get(),
            "receipt_id": _RECEIPT_ID_VAR.get(),
            "webhook_event_id": _WEBHOOK_EVENT_ID_VAR.get(),
            "outbox_event_id": _OUTBOX_EVENT_ID_VAR.get(),
            "worker_id": _WORKER_ID_VAR.get(),
            "provider_reference": _PROVIDER_REFERENCE_VAR.get(),
            "operation": _OPERATION_VAR.get(),
            "event": _EVENT_VAR.get(),
            "status": _STATUS_VAR.get(),
            "error_code": _ERROR_CODE_VAR.get(),
            "latency_ms": _LATENCY_MS_VAR.get(),
        }
    )
    return ctx


def clear_request_context() -> None:
    """Resets all async request and domain context identifiers to None."""
    _REQUEST_ID_VAR.set(None)
    _CORRELATION_ID_VAR.set(None)
    _TRACE_ID_VAR.set(None)
    _SPAN_ID_VAR.set(None)
    _TRANSACTION_ID_VAR.set(None)
    _MERCHANT_ID_VAR.set(None)
    _BUYER_ID_VAR.set(None)
    _MANDATE_ID_VAR.set(None)
    _IDEMPOTENCY_KEY_VAR.set(None)
    _EXECUTION_ATTEMPT_ID_VAR.set(None)
    _AUDIT_EVENT_ID_VAR.set(None)
    _RECEIPT_ID_VAR.set(None)
    _WEBHOOK_EVENT_ID_VAR.set(None)
    _OUTBOX_EVENT_ID_VAR.set(None)
    _WORKER_ID_VAR.set(None)
    _PROVIDER_REFERENCE_VAR.set(None)
    _OPERATION_VAR.set(None)
    _EVENT_VAR.set(None)
    _STATUS_VAR.set(None)
    _ERROR_CODE_VAR.set(None)
    _LATENCY_MS_VAR.set(None)
