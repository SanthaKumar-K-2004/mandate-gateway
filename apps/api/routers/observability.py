"""
Mandate Gateway — Observability & Prometheus Metrics Router (M29)
Workstream 3 — Exposes GET /metrics endpoint for Prometheus metrics scraping.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from apps.api.observability.prometheus_exporter import PrometheusMetricsRegistry

router = APIRouter(tags=["Observability & Prometheus Metrics"])
_registry = PrometheusMetricsRegistry()


@router.get(
    "/metrics",
    summary="Get Prometheus Text Format Metrics",
    status_code=status.HTTP_200_OK,
)
async def get_prometheus_metrics() -> Response:
    """Expose application operational metrics in Prometheus text format."""
    metrics_text = _registry.generate_prometheus_text()
    return Response(content=metrics_text, media_type="text/plain; version=0.0.4; charset=utf-8")
