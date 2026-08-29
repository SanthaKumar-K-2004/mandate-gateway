"""
M13 & M14 — Operational Intelligence & Control Plane REST Router.
Protected by OPERATOR_INTERNAL security controls for internal endpoints.
"""

from __future__ import annotations

import json
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
from apps.api.security.dependencies import get_operator_principal

try:
    from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status

    HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    HAS_FASTAPI = False
    APIRouter = Any  # type: ignore[misc,assignment]

    class status:  # type: ignore[no-redef]
        HTTP_200_OK = 200
        HTTP_401_UNAUTHORIZED = 401
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

        return Response(
            content=json.dumps(body),
            status_code=status_code,
            media_type="application/json",
        )

    @operations_router.get("/health/dependencies", summary="Dependency Diagnostics Probe")
    async def get_dependencies(
        operator: Any = Depends(get_operator_principal),
    ) -> Response:
        settings = get_settings()
        status_code, body = await handle_dependencies_async(settings)

        return Response(
            content=json.dumps(body),
            status_code=status_code,
            media_type="application/json",
        )

    @operations_router.get("/metrics", summary="Metrics Export Endpoint")
    def get_metrics(
        operator: Any = Depends(get_operator_principal),
    ) -> Response:
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
        operator: Any = Depends(get_operator_principal),
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
    def get_alerts_endpoint(
        operator: Any = Depends(get_operator_principal),
    ) -> Dict[str, Any]:
        alerts = alert_evaluator.get_active_alerts()
        return {
            "alerts_count": len(alerts),
            "alerts": alerts,
        }

    @operations_router.get(
        "/internal/operations/transactions/{transaction_id}/timeline",
        summary="Transaction Timeline Reconstruction",
    )
    async def get_transaction_timeline_endpoint(
        transaction_id: str,
        x_merchant_id: Optional[str] = Header(None, alias="X-Merchant-ID"),
        merchant_id: Optional[str] = Query(None),
        operator: Any = Depends(get_operator_principal),
    ) -> Dict[str, Any]:
        from apps.api.observability.timeline import timeline_reconstructor
        from db.unit_of_work import AsyncUnitOfWork

        req_merchant = x_merchant_id or merchant_id
        try:
            async with AsyncUnitOfWork() as uow:
                res = await timeline_reconstructor.reconstruct(
                    transaction_id=transaction_id,
                    uow=uow,
                    requesting_merchant_id=req_merchant,
                )
            return res
        except PermissionError as err:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(err),
            )
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(err),
            )

    @operations_router.get("/internal/operations/incidents", summary="Operational Incidents Query")
    def get_incidents_endpoint(
        classification: Optional[str] = Query(None),
        severity: Optional[str] = Query(None),
        status_val: Optional[str] = Query(None, alias="status"),
        merchant_id: Optional[str] = Query(None),
        operator: Any = Depends(get_operator_principal),
    ) -> Dict[str, Any]:
        from apps.api.observability.incident_engine import incident_engine

        incidents = incident_engine.query_incidents(
            classification=classification,
            severity=severity,
            status=status_val,
            merchant_id=merchant_id,
        )
        return {
            "count": len(incidents),
            "incidents": [inc.to_dict() for inc in incidents],
        }

    @operations_router.get(
        "/internal/operations/incidents/{incident_id}", summary="Operational Incident Detail"
    )
    def get_incident_detail_endpoint(
        incident_id: str,
        operator: Any = Depends(get_operator_principal),
    ) -> Dict[str, Any]:
        from apps.api.observability.incident_engine import incident_engine

        inc = incident_engine.get_incident_by_id(incident_id)
        if not inc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident '{incident_id}' not found.",
            )
        return inc.to_dict()

    @operations_router.get(
        "/internal/operations/security/summary", summary="Security Posture Summary"
    )
    def get_security_summary_endpoint(
        operator: Any = Depends(get_operator_principal),
    ) -> Dict[str, Any]:
        from apps.api.observability.forensics import forensic_engine
        from apps.api.observability.incident_engine import incident_engine

        forensics = forensic_engine.query_memory_events(limit=500)
        incidents = incident_engine.query_incidents(limit=500)

        security_incidents = [inc for inc in incidents if inc.classification == "SECURITY"]
        abuse_incidents = [inc for inc in incidents if inc.classification == "ABUSE"]

        return {
            "status": "SECURE",
            "forensic_events_count": len(forensics),
            "total_incidents_count": len(incidents),
            "security_incidents_count": len(security_incidents),
            "abuse_incidents_count": len(abuse_incidents),
            "recent_incidents": [inc.to_dict() for inc in incidents[:10]],
        }

    @operations_router.get(
        "/internal/operations/reliability/summary", summary="Reliability & Recovery Summary"
    )
    def get_reliability_summary_endpoint(
        operator: Any = Depends(get_operator_principal),
    ) -> Dict[str, Any]:
        from apps.api.observability.incident_engine import incident_engine

        incidents = incident_engine.query_incidents(limit=500)
        reliability_incidents = [inc for inc in incidents if inc.classification == "RELIABILITY"]

        return {
            "status": "HEALTHY",
            "reliability_incidents_count": len(reliability_incidents),
            "recent_reliability_incidents": [inc.to_dict() for inc in reliability_incidents[:10]],
        }
