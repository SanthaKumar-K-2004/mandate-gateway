"""
Mandate Gateway — Request Context Foundation
Section S00.5 — Observability Foundation
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


def set_request_context(
    request_id: str,
    correlation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> None:
    """Sets current async request context identifiers."""
    _REQUEST_ID_VAR.set(request_id)
    _CORRELATION_ID_VAR.set(correlation_id or request_id)
    _TRACE_ID_VAR.set(trace_id or correlation_id or request_id)


def get_request_context() -> Dict[str, Optional[str]]:
    """Returns a dictionary containing current request correlation identifiers."""
    return {
        "request_id": _REQUEST_ID_VAR.get(),
        "correlation_id": _CORRELATION_ID_VAR.get(),
        "trace_id": _TRACE_ID_VAR.get(),
    }


def clear_request_context() -> None:
    """Resets current async request context identifiers to None."""
    _REQUEST_ID_VAR.set(None)
    _CORRELATION_ID_VAR.set(None)
    _TRACE_ID_VAR.set(None)
