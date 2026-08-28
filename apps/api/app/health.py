"""
Mandate Gateway — Foundational Health & Readiness Handlers
Section S00.4 — Application Runtime Foundation
"""

from typing import Any, Dict, Tuple

from apps.api.app.lifecycle import AppLifecycle
from apps.api.config.settings import Settings


def handle_health(settings: Settings) -> Tuple[int, Dict[str, Any]]:
    """
    /health handler (Process Liveness).
    Returns 200 OK if the process is alive without connecting to external services.
    Never exposes credentials, filesystem paths, or secrets.
    """
    payload = {
        "status": "HEALTHY",
        "service": settings.app_name,
        "environment": settings.app_env.value,
    }
    return 200, payload


def handle_ready(lifecycle: AppLifecycle, settings: Settings) -> Tuple[int, Dict[str, Any]]:
    """
    /ready handler (Application Readiness).
    Returns 200 OK when application initialization completed (READY state).
    Returns 503 Service Unavailable when application is not READY (e.g. BOOTING, INITIALIZING, FAILED).
    Never exposes credentials, tracebacks, or secrets.
    """
    is_ready = lifecycle.is_ready()
    state = lifecycle.state.value

    payload = {
        "status": "READY" if is_ready else "NOT_READY",
        "state": state,
        "service": settings.app_name,
        "environment": settings.app_env.value,
    }

    status_code = 200 if is_ready else 503
    return status_code, payload
