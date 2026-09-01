"""
Mandate Gateway — Database Session & Connection Foundation.
Section S05.1 — Real Production Infrastructure Foundation.

Provides a production-grade async PostgreSQL connection layer using SQLAlchemy 2.0.
Supports explicit host/container configuration, connection pooling, health checks,
and fail-closed behavior in production mode.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from apps.api.config.helpers import get_settings
from apps.api.config.settings import Settings
from apps.api.config.types import Environment

logger = logging.getLogger("mandate_gateway.db")

_async_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_postgres_uri(settings: Settings) -> str:
    """Build PostgreSQL asyncpg connection URI safely without logging passwords."""
    user = settings.postgres_user
    password = settings.postgres_password.get_secret_value()
    host = settings.postgres_host
    port = settings.postgres_port
    db = settings.postgres_db
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def initialize_database(settings: Optional[Settings] = None) -> None:
    """
    Initialize SQLAlchemy async engine and session factory using configured Settings.
    Configures pool size, max overflow, timeout, recycle, and connection pre-ping.
    Falls back to SQLite in-memory for development/test environments when Postgres
    is unavailable (e.g. standalone host run without Docker Compose).
    """
    global _async_engine, _async_session_factory

    app_settings = settings or get_settings()

    # Production always requires real Postgres
    is_production = app_settings.app_env == Environment.PRODUCTION
    is_test_mode = app_settings.app_env == Environment.TEST

    uri = get_postgres_uri(app_settings)

    try:
        _async_engine = create_async_engine(
            uri,
            pool_size=10,
            max_overflow=20,
            pool_timeout=5,
            pool_recycle=1800,
            pool_pre_ping=True,
            echo=False,
            connect_args={"timeout": 3},
        )
        _async_session_factory = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        logger.info(
            "SQLAlchemy async engine initialized successfully for host '%s'",
            app_settings.postgres_host,
        )
    except Exception as exc:
        logger.error("Failed to initialize database engine: %s", exc)
        if is_production:
            raise RuntimeError(
                f"Database initialization failed in production environment: {exc}"
            ) from exc
        # Non-production fallback: SQLite in-memory for standalone/demo mode
        logger.warning(
            "Postgres unavailable — falling back to SQLite in-memory for standalone demo mode."
        )
        try:
            _async_engine = create_async_engine(
                "sqlite+aiosqlite:///:memory:",
                connect_args={"check_same_thread": False},
                echo=False,
            )
            _async_session_factory = async_sessionmaker(
                bind=_async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
            _sqlite_fallback_active = True
        except Exception as sqlite_exc:
            logger.error("SQLite fallback also failed: %s", sqlite_exc)
            if not is_test_mode:
                raise RuntimeError(
                    f"Database initialization failed (both Postgres and SQLite fallback): {sqlite_exc}"
                ) from sqlite_exc


_sqlite_fallback_active: bool = False


async def ensure_sqlite_tables() -> None:
    """Create all schema tables when running with SQLite in-memory fallback.
    Must be called once before any DB operations when the fallback is active.
    """
    global _sqlite_fallback_active
    if not _sqlite_fallback_active or _async_engine is None:
        return
    from db.models.base import Base
    # Import all models so their metadata is registered
    import db.models.merchant  # noqa: F401
    import db.models.mandate  # noqa: F401
    import db.models.policy  # noqa: F401
    import db.models.transaction  # noqa: F401
    import db.models.outbox  # noqa: F401
    import db.models.audit  # noqa: F401
    import db.models.budget  # noqa: F401
    import db.models.product  # noqa: F401
    import db.models.credential  # noqa: F401
    import db.models.replay  # noqa: F401
    import db.models.step_up  # noqa: F401
    import db.models.webhook  # noqa: F401
    import db.models.receipt  # noqa: F401
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _sqlite_fallback_active = False  # Tables created, no need to re-run
    logger.info("SQLite in-memory schema created successfully (standalone demo mode).")


async def close_database() -> None:
    """Close SQLAlchemy async engine and dispose connection pool."""
    global _async_engine, _async_session_factory
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
        logger.info("Database engine disposed and connections closed.")


async def check_database_health(settings: Optional[Settings] = None) -> Dict[str, Any]:
    """
    Perform an actual database health check by executing 'SELECT 1'.
    Returns structured health status dictionary without exposing credentials.
    """
    app_settings = settings or get_settings()
    health_status: Dict[str, Any] = {
        "status": "UNAVAILABLE",
        "configured": True,
        "connected": False,
        "host": app_settings.postgres_host,
        "port": app_settings.postgres_port,
        "database": app_settings.postgres_db,
        "error": None,
    }

    if _async_engine is None:
        health_status["error"] = "Engine not initialized"
        return health_status

    try:
        async with _async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            if val == 1:
                health_status["status"] = "CONNECTED"
                health_status["connected"] = True
    except Exception as exc:
        health_status["status"] = "UNAVAILABLE"
        health_status["connected"] = False
        health_status["error"] = str(exc)

    return health_status


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager producing an independent database session.
    Automatically commits on success or rolls back on exception.
    """
    if _async_session_factory is None:
        raise RuntimeError(
            "Database session factory is not initialized. Call initialize_database() first."
        )

    session = _async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_async_session_factory() -> Optional[async_sessionmaker[AsyncSession]]:
    """Return active async sessionmaker factory."""
    return _async_session_factory

