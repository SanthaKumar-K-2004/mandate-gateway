"""
Mandate Gateway — Redis Connection Foundation.
Section S05.1 — Real Production Infrastructure Foundation.

Provides an official Redis asyncio client connection layer.
Supports host/container configuration, connection health checks,
and fail-closed security in production mode.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

try:
    import redis.asyncio as aioredis

    HAS_REDIS = True
except ImportError:
    aioredis = None  # type: ignore[assignment]
    HAS_REDIS = False

from apps.api.config.helpers import get_settings
from apps.api.config.settings import Settings
from apps.api.config.types import Environment

logger = logging.getLogger("mandate_gateway.redis")

_redis_client: Optional[Any] = None


def initialize_redis(settings: Optional[Settings] = None) -> None:
    """Initialize Redis asyncio client using configured Settings."""
    global _redis_client

    app_settings = settings or get_settings()
    is_test_mode = app_settings.app_env == Environment.TEST

    if not HAS_REDIS or aioredis is None:
        logger.warning("redis package not installed; skipping Redis client initialization")
        return

    try:
        _redis_client = aioredis.Redis(
            host=app_settings.redis_host,
            port=app_settings.redis_port,
            db=app_settings.redis_db,
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
        logger.info(
            "Redis client initialized for host '%s:%d' (db=%d)",
            app_settings.redis_host,
            app_settings.redis_port,
            app_settings.redis_db,
        )
    except Exception as exc:
        logger.error("Failed to initialize Redis client: %s", exc)
        if not is_test_mode:
            raise RuntimeError(
                f"Redis initialization failed in production environment: {exc}"
            ) from exc


async def close_redis() -> None:
    """Close Redis client connection pool."""
    global _redis_client
    if _redis_client is not None:
        if hasattr(_redis_client, "aclose"):
            await _redis_client.aclose()
        else:
            await _redis_client.close()
        _redis_client = None
        logger.info("Redis client connections closed.")


async def check_redis_health(settings: Optional[Settings] = None) -> Dict[str, Any]:
    """
    Perform an actual Redis health check by executing 'ping()'.
    Returns structured health status dictionary.
    """
    app_settings = settings or get_settings()
    health_status: Dict[str, Any] = {
        "status": "UNAVAILABLE",
        "configured": True,
        "connected": False,
        "host": app_settings.redis_host,
        "port": app_settings.redis_port,
        "db": app_settings.redis_db,
        "error": None,
    }

    if not HAS_REDIS or aioredis is None:
        health_status["error"] = "redis package not installed"
        return health_status

    if _redis_client is None:
        health_status["error"] = "Redis client not initialized"
        return health_status

    try:
        ping_res = await _redis_client.ping()
        if ping_res is True or str(ping_res).upper() == "PONG":
            health_status["status"] = "CONNECTED"
            health_status["connected"] = True
    except Exception as exc:
        health_status["status"] = "UNAVAILABLE"
        health_status["connected"] = False
        health_status["error"] = str(exc)

    return health_status


def get_redis_client() -> aioredis.Redis:
    """Return active Redis client or raise RuntimeError if uninitialized."""
    if _redis_client is None:
        raise RuntimeError("Redis client is not initialized. Call initialize_redis() first.")
    return _redis_client
