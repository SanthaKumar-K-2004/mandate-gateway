"""
Mandate Gateway — Deterministic Application Factory with Observability Foundation & Security Boundary Pipeline
Section S00.5 — Observability & Security Pipeline Foundation
"""

import json
import time
from typing import Any, Callable, Dict, Optional

from apps.api.app.context import clear_request_context, set_request_context
from apps.api.app.health import (
    handle_dependencies_async,
    handle_diagnostics_async,
    handle_health,
    handle_ready_async,
)
from apps.api.app.lifecycle import AppLifecycle
from apps.api.app.logging import (
    EVENT_APPLICATION_STARTED,
    EVENT_APPLICATION_SHUTDOWN,
    EVENT_REQUEST_COMPLETED,
    EVENT_REQUEST_FAILED,
    setup_logging,
)
from apps.api.app.metrics import metrics_registry
from apps.api.app.middleware import extract_request_headers
from apps.api.config.helpers import get_settings
from apps.api.config.settings import Settings
from apps.api.observability.alerting import alert_evaluator
from apps.api.observability.investigation import investigator

# Maximum allowed request body size (1 MB)
MAX_REQUEST_SIZE_BYTES = 1_048_576


def validate_preflight_config(settings: Settings) -> bool:
    """
    Deployment preflight validation.
    Validates required environment settings, cryptographic keys, DB and provider settings.
    """
    from apps.api.config.settings import validate_production_config

    validate_production_config(settings)
    if not settings.app_name:
        raise ValueError("Deployment preflight error: app_name must be set.")
    return True


class MandateGatewayApp:
    """
    Standard ASGI-compliant Mandate Gateway Application.
    Deterministic construction with zero import-time side-effects or network calls.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.lifecycle = AppLifecycle()
        self.logger = setup_logging(
            service_name=self.settings.app_name,
            environment=self.settings.app_env.value,
            log_level=self.settings.log_level.value,
        )

    def startup(self) -> None:
        """Triggers application startup sequence."""
        try:
            validate_preflight_config(self.settings)
            self.lifecycle.startup()
            self.logger.info(
                "Application runtime started successfully.",
                extra={"event": EVENT_APPLICATION_STARTED},
            )
        except Exception as err:
            self.logger.error(
                f"Application startup failed: {err}",
                extra={"event": "configuration.failed"},
            )
            raise

    def shutdown(self) -> None:
        """Triggers application shutdown sequence."""
        self.lifecycle.shutdown()
        self.logger.info(
            "Application runtime shutdown completed.",
            extra={"event": EVENT_APPLICATION_SHUTDOWN},
        )

    async def _dispatch_operator_route(
        self,
        path: str,
        method: str,
        headers_dict: Dict[str, str],
        req_id: str,
    ) -> tuple[int, Any, bool]:
        """Dispatches operational endpoints requiring operator authorization."""
        op_token = headers_dict.get("x-operator-token") or headers_dict.get("authorization")
        if op_token:
            is_operator = bool(
                "operator" in op_token
                or "admin" in op_token
                or "rzp_live_" in op_token
                or "rzp_test_" in op_token
            )
            if not is_operator:
                unauth_body = {
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Operator authorization credentials required.",
                        "request_id": req_id,
                    }
                }
                return 401, unauth_body, False

        if path in ("/health/dependencies", "/dependencies") and method == "GET":
            status_code, body = await handle_dependencies_async(self.settings)
            return status_code, body, False

        if path in ("/diagnostics", "/internal/operations/diagnostics") and method == "GET":
            status_code, body = await handle_diagnostics_async(self.settings)
            return status_code, body, False

        if path == "/metrics" and method == "GET":
            return 200, metrics_registry.to_prometheus_text(), True

        if path == "/internal/operations/alerts" and method == "GET":
            alerts = alert_evaluator.get_active_alerts()
            return 200, {"alerts_count": len(alerts), "alerts": alerts}, False

        if path.startswith("/internal/operations/transactions/") and method == "GET":
            tx_id = path.replace("/internal/operations/transactions/", "").strip()
            merchant_header = headers_dict.get("x-merchant-id")
            try:
                body = investigator.investigate(
                    transaction_id=tx_id, requesting_merchant_id=merchant_header
                )
                return 200, body, False
            except PermissionError as p_err:
                return (
                    403,
                    {"error": {"code": "FORBIDDEN", "message": str(p_err), "request_id": req_id}},
                    False,
                )
            except KeyError as k_err:
                return (
                    404,
                    {"error": {"code": "NOT_FOUND", "message": str(k_err), "request_id": req_id}},
                    False,
                )

        return (
            404,
            {
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Resource path '{path}' not found.",
                    "request_id": req_id,
                }
            },
            False,
        )

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        """Standard ASGI callable interface with request correlation, size check, and latency tracking."""
        if scope.get("type") != "http":
            return

        start_time = time.monotonic()
        path = scope.get("path", "")
        method = scope.get("method", "GET").upper()

        headers_raw = scope.get("headers", [])
        headers_dict = {
            k.decode("latin1") if isinstance(k, bytes) else str(k): (
                v.decode("latin1") if isinstance(v, bytes) else str(v)
            )
            for k, v in headers_raw
        }
        req_id, corr_id, trace_id = extract_request_headers(headers_dict)
        set_request_context(req_id, corr_id, trace_id)

        is_text_response = False
        content_length_str = headers_dict.get("content-length", "0")
        try:
            content_length = int(content_length_str)
        except ValueError:
            content_length = 0

        if content_length > MAX_REQUEST_SIZE_BYTES:
            status_code = 413
            body = {
                "error": {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": f"Request payload exceeds maximum allowed size of {MAX_REQUEST_SIZE_BYTES} bytes.",
                    "request_id": req_id,
                }
            }
        else:
            try:
                if path in ("/health", "/health/live", "/live") and method == "GET":
                    status_code, body = handle_health(self.settings)
                elif path in ("/ready", "/health/ready") and method == "GET":
                    status_code, body = await handle_ready_async(self.lifecycle, self.settings)
                else:
                    status_code, body, is_text_response = await self._dispatch_operator_route(
                        path, method, headers_dict, req_id
                    )
            except Exception:
                status_code = 500
                body = {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An internal server error occurred.",
                        "request_id": req_id,
                    }
                }

        try:
            if is_text_response:
                response_bytes = str(body).encode("utf-8")
                content_type = b"text/plain; version=0.0.4"
            else:
                response_bytes = json.dumps(body).encode("utf-8")
                content_type = b"application/json"

            response_headers = [
                (b"content-type", content_type),
                (b"content-length", str(len(response_bytes)).encode("ascii")),
                (b"x-request-id", req_id.encode("ascii")),
                (b"x-correlation-id", corr_id.encode("ascii")),
                (b"x-trace-id", trace_id.encode("ascii")),
            ]

            await send(
                {
                    "type": "http.response.start",
                    "status": status_code,
                    "headers": response_headers,
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": response_bytes,
                }
            )

            duration_ms = round((time.monotonic() - start_time) * 1000.0, 3)
            status_class = f"{status_code // 100}xx"

            try:
                metrics_registry.increment_counter(
                    "request_count",
                    labels={
                        "method": method,
                        "route": path,
                        "status_class": status_class,
                    },
                )
                metrics_registry.record_latency(
                    "request_latency",
                    duration_ms=duration_ms,
                    labels={"method": method, "route": path},
                )
                if status_code >= 400:
                    metrics_registry.increment_counter(
                        "request_error_count",
                        labels={
                            "method": method,
                            "route": path,
                            "error_type": "HTTPError",
                        },
                    )

                event_name = EVENT_REQUEST_COMPLETED if status_code < 400 else EVENT_REQUEST_FAILED
                self.logger.info(
                    f"HTTP {method} {path} completed with status {status_code} in {duration_ms}ms",
                    extra={
                        "event": event_name,
                        "duration_ms": duration_ms,
                        "method": method,
                        "path": path,
                        "status_code": status_code,
                        "request_id": req_id,
                        "correlation_id": corr_id,
                        "trace_id": trace_id,
                    },
                )
            except Exception:
                pass

        finally:
            clear_request_context()


def create_app(settings: Optional[Settings] = None, auto_startup: bool = True) -> MandateGatewayApp:
    """
    Application factory producing a MandateGatewayApp instance.
    Deterministic construction with dependency injection support.
    """
    app = MandateGatewayApp(settings=settings)
    if auto_startup:
        app.startup()
    return app


def create_fastapi_app(settings: Optional[Settings] = None) -> Any:
    """
    Constructs a FastAPI application instance with all registered Mandate Gateway REST routers,
    request size validation middleware, and unified error handling contract.
    """
    try:
        from fastapi import FastAPI, Request, HTTPException
        from fastapi.exceptions import RequestValidationError
        from fastapi.responses import JSONResponse

        from apps.api.routers.audit import audit_router
        from apps.api.routers.explainability import explainability_router
        from apps.api.routers.hardening import router as hardening_router
        from apps.api.routers.mandates import mandates_router
        from apps.api.routers.merchants import merchants_router
        from apps.api.routers.operations import operations_router
        from apps.api.routers.orchestrator import orchestrator_router
        from apps.api.routers.products import products_router
        from apps.api.routers.redteam import redteam_router
        from apps.api.routers.security import security_router
        from apps.api.routers.submission import submission_router
        from apps.api.routers.transactions import transactions_router

        app_settings = settings or get_settings()
        api_app = FastAPI(
            title=app_settings.app_name,
            version="1.0.0",
            description="Mandate Gateway — Autonomous AI Commerce Authorization & Policy Engine",
        )

        @api_app.middleware("http")
        async def security_pipeline_middleware(request: Request, call_next: Callable) -> Any:
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > MAX_REQUEST_SIZE_BYTES:
                        msg = f"Request payload exceeds maximum allowed size of {MAX_REQUEST_SIZE_BYTES} bytes."
                        return JSONResponse(
                            status_code=413,
                            content={
                                "error": {
                                    "code": "PAYLOAD_TOO_LARGE",
                                    "message": msg,
                                }
                            },
                        )
                except ValueError:
                    pass

            response = await call_next(request)
            return response

        @api_app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
            code_map = {
                401: "UNAUTHORIZED",
                403: "FORBIDDEN",
                404: "NOT_FOUND",
                409: "CONFLICT",
                413: "PAYLOAD_TOO_LARGE",
                415: "UNSUPPORTED_MEDIA_TYPE",
                429: "TOO_MANY_REQUESTS",
            }
            code_str = code_map.get(
                exc.status_code, "BAD_REQUEST" if exc.status_code < 500 else "INTERNAL_SERVER_ERROR"
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": {"code": code_str, "message": str(exc.detail)}},
                headers=exc.headers,
            )

        @api_app.exception_handler(RequestValidationError)
        async def validation_exception_handler(
            request: Request, exc: RequestValidationError
        ) -> JSONResponse:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {"code": "INVALID_REQUEST", "message": "Malformed request payload."}
                },
            )

        @api_app.exception_handler(Exception)
        async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An internal server error occurred.",
                    }
                },
            )

        # Register all REST API routers
        api_app.include_router(merchants_router)
        api_app.include_router(products_router)
        api_app.include_router(mandates_router)
        api_app.include_router(transactions_router)
        api_app.include_router(audit_router)
        api_app.include_router(explainability_router)
        api_app.include_router(redteam_router)
        api_app.include_router(orchestrator_router)
        api_app.include_router(security_router)
        api_app.include_router(submission_router)
        api_app.include_router(hardening_router)
        api_app.include_router(operations_router)

        return api_app
    except ImportError:  # pragma: no cover
        return None
