"""
Mandate Gateway — Application Runtime Package Root
Section S00.5 — Observability Foundation
"""

from apps.api.app.context import (
    clear_request_context,
    get_request_context,
    set_request_context,
)
from apps.api.app.errors import (
    ConfigurationError,
    RuntimeErrorBase,
    RuntimeInitializationError,
)
from apps.api.app.factory import MandateGatewayApp, create_app
from apps.api.app.lifecycle import AppLifecycle, LifecycleState
from apps.api.app.metrics import MetricsRegistry, metrics_registry

__all__ = [
    "create_app",
    "MandateGatewayApp",
    "AppLifecycle",
    "LifecycleState",
    "RuntimeErrorBase",
    "ConfigurationError",
    "RuntimeInitializationError",
    "set_request_context",
    "get_request_context",
    "clear_request_context",
    "MetricsRegistry",
    "metrics_registry",
]
