"""
Mandate Gateway — Request Context Foundation
Section S00.5 & M08 — Observability Foundation & Transaction Correlation
"""

import contextvars
from typing import Dict, Optional

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
_EXECUTION_ATTEMPT_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "execution_attempt_id", default=None
)
_OUTBOX_EVENT_ID_VAR: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "outbox_event_id", default=None
)


def set_request_context(
    request_id: str,
    correlation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> None:
    """Sets current async request context identifiers."""
    _REQUEST_ID_VAR.set(request_id)
    _CORRELATION_ID_VAR.set(correlation_id or request_id)
    _TRACE_ID_VAR.set(trace_id or correlation_id or request_id)


def set_transaction_context(
    transaction_id: Optional[str] = None,
    merchant_id: Optional[str] = None,
    buyer_id: Optional[str] = None,
    mandate_id: Optional[str] = None,
    execution_attempt_id: Optional[str] = None,
    outbox_event_id: Optional[str] = None,
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
    if execution_attempt_id is not None:
        _EXECUTION_ATTEMPT_ID_VAR.set(execution_attempt_id)
    if outbox_event_id is not None:
        _OUTBOX_EVENT_ID_VAR.set(outbox_event_id)


def get_request_context() -> Dict[str, Optional[str]]:
    """Returns a dictionary containing current request correlation identifiers."""
    return {
        "request_id": _REQUEST_ID_VAR.get(),
        "correlation_id": _CORRELATION_ID_VAR.get(),
        "trace_id": _TRACE_ID_VAR.get(),
    }


def get_full_context() -> Dict[str, Optional[str]]:
    """Returns all request and domain operation context identifiers."""
    ctx = get_request_context()
    ctx.update(
        {
            "transaction_id": _TRANSACTION_ID_VAR.get(),
            "merchant_id": _MERCHANT_ID_VAR.get(),
            "buyer_id": _BUYER_ID_VAR.get(),
            "mandate_id": _MANDATE_ID_VAR.get(),
            "execution_attempt_id": _EXECUTION_ATTEMPT_ID_VAR.get(),
            "outbox_event_id": _OUTBOX_EVENT_ID_VAR.get(),
        }
    )
    return ctx


def clear_request_context() -> None:
    """Resets all async request and domain context identifiers to None."""
    _REQUEST_ID_VAR.set(None)
    _CORRELATION_ID_VAR.set(None)
    _TRACE_ID_VAR.set(None)
    _TRANSACTION_ID_VAR.set(None)
    _MERCHANT_ID_VAR.set(None)
    _BUYER_ID_VAR.set(None)
    _MANDATE_ID_VAR.set(None)
    _EXECUTION_ATTEMPT_ID_VAR.set(None)
    _OUTBOX_EVENT_ID_VAR.set(None)
