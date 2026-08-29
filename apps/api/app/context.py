"""
Mandate Gateway — Request Context Foundation
Section S00.5 & M08 — Observability Foundation & Transaction Correlation
"""

import contextvars
from typing import Any, Dict, Optional

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

# ContextVars for domain transaction correlation propagation
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
_OUTBOX_EVENT_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "outbox_event_id", default=None
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


def set_request_context(
    request_id: str,
    correlation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
) -> None:
    """Sets current async request context identifiers."""
    _REQUEST_ID_VAR.set(request_id)
    _CORRELATION_ID_VAR.set(correlation_id or request_id)
    _TRACE_ID_VAR.set(trace_id or correlation_id or request_id)
    if span_id is not None:
        _SPAN_ID_VAR.set(span_id)


def set_transaction_context(
    transaction_id: Optional[str] = None,
    merchant_id: Optional[str] = None,
    buyer_id: Optional[str] = None,
    mandate_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    execution_attempt_id: Optional[str] = None,
    outbox_event_id: Optional[str] = None,
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
    if outbox_event_id is not None:
        _OUTBOX_EVENT_ID_VAR.set(outbox_event_id)
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
            "outbox_event_id": _OUTBOX_EVENT_ID_VAR.get(),
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
    _OUTBOX_EVENT_ID_VAR.set(None)
    _PROVIDER_REFERENCE_VAR.set(None)
    _OPERATION_VAR.set(None)
    _EVENT_VAR.set(None)
    _STATUS_VAR.set(None)
    _ERROR_CODE_VAR.set(None)
    _LATENCY_MS_VAR.set(None)
