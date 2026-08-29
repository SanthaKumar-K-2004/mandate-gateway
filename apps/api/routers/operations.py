"""
M13 — Operational Intelligence & Control Plane REST Router.
Section 13 — API Design
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from apps.api.app.health import (
    handle_dependencies_async,
    handle_health,
    handle_ready_async,
)
from apps.api.app.lifecycle import AppLifecycle
from apps.api.app.metrics import metrics_registry
from apps.api.config.helpers import get_settings
from apps.api.observability.alerting import alert_evaluator
from apps.api.observability.investigation import investigator

try:
    from fastapi import APIRouter, Header, HTTPException, Query, Response, status

    HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    HAS_FASTAPI = False
    APIRouter = Any  # type: ignore[misc,assignment]

    class status:  # type: ignore[no-redef]
        HTTP_200_OK = 200
        HTTP_403_FORBIDDEN = 403
        HTTP_404_NOT_FOUND = 404
        HTTP_503_SERVICE_UNAVAILABLE = 503

    class HTTPException(Exception):  # type: ignore[no-redef]
        def __init__(self, status_code: int, detail: str) -> None:
            self.status_code = status_code
            self.detail = detail


if HAS_FASTAPI:
    operations_router: Any = APIRouter(tags=["Operational Intelligence & Control Plane"])
else:

    class DummyRouter:
        def get(self, *args: Any, **kwargs: Any) -> Callable:
            def decorator(func: Callable) -> Callable:
                return func

            return decorator

    operations_router = DummyRouter()


if HAS_FASTAPI:

    @operations_router.get("/health/live", summary="Process Liveness Probe")
    def get_liveness() -> Dict[str, Any]:
        settings = get_settings()
        _, body = handle_health(settings)
        return body

    @operations_router.get("/health/ready", summary="Application Readiness Probe")
    async def get_readiness() -> Response:
        settings = get_settings()
        lifecycle = AppLifecycle()
        lifecycle.startup()  # Mark ready for router evaluation if initialized
        status_code, body = await handle_ready_async(lifecycle, settings)
        import json

        return Response(
            content=json.dumps(body),
            status_code=status_code,
            media_type="application/json",
        )

    @operations_router.get("/health/dependencies", summary="Dependency Diagnostics Probe")
    async def get_dependencies() -> Response:
        settings = get_settings()
        status_code, body = await handle_dependencies_async(settings)
        import json

        return Response(
            content=json.dumps(body),
            status_code=status_code,
            media_type="application/json",
        )

    @operations_router.get("/metrics", summary="Metrics Export Endpoint")
    def get_metrics() -> Response:
        content = metrics_registry.to_prometheus_text()
        return Response(content=content, media_type="text/plain; version=0.0.4")

    @operations_router.get(
        "/internal/operations/transactions/{transaction_id}",
        summary="Operational Transaction Investigation",
    )
    def investigate_transaction_endpoint(
        transaction_id: str,
        x_merchant_id: Optional[str] = Header(None, alias="X-Merchant-ID"),
        merchant_id: Optional[str] = Query(None),
    ) -> Dict[str, Any]:
        req_merchant = x_merchant_id or merchant_id
        try:
            return investigator.investigate(
                transaction_id=transaction_id,
                requesting_merchant_id=req_merchant,
            )
        except PermissionError as err:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(err),
            )
        except KeyError as err:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(err),
            )

    @operations_router.get("/internal/operations/alerts", summary="Operational Alert Status")
    def get_alerts_endpoint() -> Dict[str, Any]:
        alerts = alert_evaluator.get_active_alerts()
        return {
            "alerts_count": len(alerts),
            "alerts": alerts,
        }
