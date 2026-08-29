"""
Mandate Gateway — OpenTelemetry-Compatible Distributed Tracing Architecture
Milestone M13 — Operational Observability Foundation

Instruments major execution boundaries:
HTTP Request -> Authorization -> Mandate -> Policy -> Budget -> Replay -> Nonce ->
Transaction Creation -> Execution Claim -> Provider Dispatch -> Transaction Finalization ->
Audit Ledger -> Receipt Creation -> Transactional Outbox.

FAIL-OPEN GUARANTEE: Telemetry exporter errors or trace collection failures MUST NOT
interrupt safe payment execution or transaction state consistency.
"""

from __future__ import annotations

import functools
import inspect
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Literal, Optional, TypeVar

from apps.api.app.context import get_full_context, get_request_context, set_request_context

logger = logging.getLogger("mandate_gateway.tracing")

F = TypeVar("F", bound=Callable[..., Any])


class Span:
    """Represents an execution boundary span."""

    def __init__(
        self,
        name: str,
        span_id: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.attributes: Dict[str, Any] = attributes or {}
        self.start_time = time.monotonic()
        self.end_time: Optional[float] = None
        self.status = "OK"
        self.error: Optional[str] = None

    def set_attribute(self, key: str, value: Any) -> None:
        """Sets a span attribute safely."""
        self.attributes[key] = value

    def set_error(self, err: Exception) -> None:
        """Records an error status on the span."""
        self.status = "ERROR"
        self.error = str(err)

    def finish(self) -> float:
        """Ends the span and returns duration in ms."""
        self.end_time = time.monotonic()
        return round((self.end_time - self.start_time) * 1000.0, 3)


class Tracer:
    """OpenTelemetry-compatible tracer with fail-open guarantee."""

    def __init__(self, service_name: str = "mandate-gateway") -> None:
        self.service_name = service_name
        self._completed_spans: List[Span] = []

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Span:
        """Starts a new span and enriches request context."""
        try:
            req_ctx = get_request_context()
            parent_span_id = req_ctx.get("span_id")
            span_id = str(uuid.uuid4())[:16]

            set_request_context(
                request_id=req_ctx.get("request_id") or str(uuid.uuid4()),
                correlation_id=req_ctx.get("correlation_id"),
                trace_id=req_ctx.get("trace_id"),
                span_id=span_id,
            )

            span_attrs = attributes or {}
            full_ctx = get_full_context()
            for key in ("transaction_id", "merchant_id", "buyer_id", "mandate_id"):
                if full_ctx.get(key) is not None:
                    span_attrs.setdefault(key, full_ctx[key])

            return Span(
                name=name,
                span_id=span_id,
                parent_span_id=parent_span_id,
                attributes=span_attrs,
            )
        except Exception as err:
            logger.warning(f"Fail-open tracing start_span error: {err}")
            return Span(name=name, span_id="fallback-span")

    def end_span(self, span: Span, err: Optional[Exception] = None) -> None:
        """Ends a span and safely records completed span without interrupting execution."""
        try:
            if err is not None:
                span.set_error(err)
            duration_ms = span.finish()
            self._completed_spans.append(span)

            logger.debug(
                f"Trace Span '{span.name}' completed in {duration_ms}ms (status={span.status})",
                extra={
                    "span_id": span.span_id,
                    "parent_span_id": span.parent_span_id,
                    "duration_ms": duration_ms,
                    "status": span.status,
                },
            )
        except Exception as tracer_err:
            logger.warning(f"Fail-open tracing end_span error: {tracer_err}")

    def get_completed_spans(self) -> List[Span]:
        """Returns completed spans (for operational analysis and tests)."""
        return list(self._completed_spans)

    def clear(self) -> None:
        """Clears completed spans."""
        self._completed_spans.clear()


# Global singleton tracer
tracer = Tracer()


class TraceSpanContextManager:
    """Async & sync context manager for boundary tracing with fail-open semantics."""

    def __init__(self, span_name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.span_name = span_name
        self.attributes = attributes
        self.span: Optional[Span] = None

    def __enter__(self) -> Span:
        try:
            self.span = tracer.start_span(self.span_name, self.attributes)
            return self.span
        except Exception as err:
            logger.warning(f"Fail-open tracing context manager enter error: {err}")
            self.span = Span(name=self.span_name, span_id="fallback-span")
            return self.span

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Literal[False]:
        try:
            if self.span:
                err = exc_val if isinstance(exc_val, Exception) else None
                tracer.end_span(self.span, err=err)
        except Exception as err:
            logger.warning(f"Fail-open tracing context manager exit error: {err}")
        return False  # Never suppress original exception if one occurred in payment logic

    async def __aenter__(self) -> Span:
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Literal[False]:
        return self.__exit__(exc_type, exc_val, exc_tb)


def trace_span(span_name: str, attributes: Optional[Dict[str, Any]] = None) -> Callable[[F], F]:
    """Decorator to instrument functions with tracing boundaries."""

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with TraceSpanContextManager(span_name, attributes):
                    return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with TraceSpanContextManager(span_name, attributes):
                    return func(*args, **kwargs)

            return sync_wrapper  # type: ignore[return-value]

    return decorator
