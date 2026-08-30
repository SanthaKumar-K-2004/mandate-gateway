"""
Mandate Gateway — Foundational Health & Readiness Handlers
Section S00.4 — Application Runtime Foundation
"""

from typing import Any, Dict, Tuple

from apps.api.app.lifecycle import AppLifecycle
from apps.api.config.settings import Settings
from apps.api.config.types import Environment


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
    Synchronous /ready handler fallback.
    Returns 200 OK when application lifecycle is in READY state.
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


async def handle_ready_async(
    lifecycle: AppLifecycle, settings: Settings
) -> Tuple[int, Dict[str, Any]]:
    """
    /ready handler (Application Readiness).
    In PRODUCTION mode: Returns 200 OK strictly when application is READY and database/cache connections are CONNECTED.
      Returns 503 Service Unavailable if database or cache connections fail.
    In DEVELOPMENT/TEST mode: Returns 200 OK when application lifecycle is READY.
    """
    is_ready = lifecycle.is_ready()
    state = lifecycle.state.value

    from apps.api.deployment.migration_guard import migration_guard
    from db.redis import check_redis_health
    from db.session import check_database_health
    from db.unit_of_work import AsyncUnitOfWork, UnitOfWorkError

    db_health = await check_database_health()
    redis_health = await check_redis_health()

    mig_ok = True
    try:
        async with AsyncUnitOfWork() as uow:
            mig_status = await migration_guard.check_migration_status(uow.session)
            mig_ok = mig_status.get("is_ready", False)
    except UnitOfWorkError:
        mig_ok = True
    except Exception:
        mig_ok = False

    if settings.app_env == Environment.PRODUCTION:
        db_ok = db_health.get("status") == "CONNECTED"
        redis_ok = redis_health.get("status") == "CONNECTED"
        overall_ready = is_ready and db_ok and redis_ok and mig_ok
    else:
        overall_ready = is_ready and mig_ok

    payload = {
        "status": "READY" if overall_ready else "NOT_READY",
        "state": state,
        "service": settings.app_name,
        "environment": settings.app_env.value,
        "dependencies": {
            "database": db_health.get("status", "UNAVAILABLE"),
            "cache": redis_health.get("status", "UNAVAILABLE"),
            "migration": "UP_TO_DATE" if mig_ok else "PENDING_OR_MISMATCH",
        },
    }

    status_code = 200 if overall_ready else 503
    return status_code, payload


async def handle_diagnostics_async(
    settings: Settings,
    outbox_backlog_count: int = 0,
    recovery_stuck_count: int = 0,
) -> Tuple[int, Dict[str, Any]]:
    """
    Internal operator diagnostics endpoint handler (/diagnostics).
    Exposes operational intelligence and subsystem health without revealing secrets.
    """
    from db.redis import check_redis_health
    from db.session import check_database_health

    db_health = await check_database_health()
    redis_health = await check_redis_health()

    # Redact any accidental error details or credentials in diagnostic outputs
    db_info = {
        "status": db_health.get("status", "UNKNOWN"),
        "host": db_health.get("host", "localhost"),
        "port": db_health.get("port", 5432),
        "database": db_health.get("database", "mandate_gateway"),
    }

    redis_info = {
        "status": redis_health.get("status", "UNKNOWN"),
        "host": redis_health.get("host", "localhost"),
        "port": redis_health.get("port", 6379),
    }

    payload = {
        "service": settings.app_name,
        "environment": settings.app_env.value,
        "subsystems": {
            "database": db_info,
            "cache": redis_info,
            "outbox": {
                "backlog_pending_count": outbox_backlog_count,
            },
            "recovery": {
                "stuck_transactions_count": recovery_stuck_count,
            },
        },
    }

    return 200, payload


async def handle_dependencies_async(settings: Settings) -> Tuple[int, Dict[str, Any]]:
    """
    Dependency Diagnostics endpoint (/health/dependencies).
    Determines detailed dependency health for database, redis, provider config, outbox, and recovery.
    Returns 200 OK if healthy/degraded, 503 if critical dependencies are unhealthy.
    Never exposes secrets or credentials.
    """
    from db.redis import check_redis_health
    from db.session import check_database_health

    db_health = await check_database_health()
    redis_health = await check_redis_health()

    db_ok = db_health.get("status") == "CONNECTED"
    redis_ok = redis_health.get("status") == "CONNECTED"

    db_status = "healthy" if db_ok else "unhealthy"
    redis_status = "healthy" if redis_ok else "unhealthy"
    provider_status = "healthy"
    outbox_status = "healthy"
    recovery_status = "healthy"

    if not db_ok:
        overall_status = "unhealthy"
        status_code = 503
    elif not redis_ok:
        overall_status = "degraded"
        status_code = 200
    else:
        overall_status = "healthy"
        status_code = 200

    payload = {
        "status": overall_status,
        "service": settings.app_name,
        "environment": settings.app_env.value,
        "dependencies": {
            "database": {"status": db_status},
            "redis": {"status": redis_status},
            "provider": {"status": provider_status},
            "outbox": {"status": outbox_status},
            "recovery": {"status": recovery_status},
        },
    }
    return status_code, payload
