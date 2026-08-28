"""
Security tests for M05.1 Infrastructure & Fail-Closed Behavior.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from apps.api.config.settings import Settings
from apps.api.config.types import Environment, LogLevel, SecretString
from db.redis import check_redis_health, close_redis, initialize_redis
from db.session import (
    check_database_health,
    close_database,
    initialize_database,
)


class TestM051InfrastructureSecurity(unittest.TestCase):
    """Security tests for fail-closed behavior, secret redaction, and health semantics."""

    def setUp(self) -> None:
        self.prod_settings = Settings(
            app_env=Environment.PRODUCTION,
            app_name="mandate-gateway",
            log_level=LogLevel.INFO,
            host_context=False,
            postgres_host="invalid_db_host",
            postgres_port=5432,
            postgres_db="mandate_prod",
            postgres_user="postgres",
            postgres_password=SecretString("PROD_SECRET_PASSWORD_99"),
            redis_host="invalid_redis_host",
            redis_port=6379,
            redis_db=0,
        )

    def test_database_secret_never_exposed_in_health(self) -> None:
        """Verify database password never leaks into health status dictionaries or string representations."""
        initialize_database(self.prod_settings)
        health = asyncio.run(check_database_health(self.prod_settings))
        health_str = str(health)
        self.assertNotIn("PROD_SECRET_PASSWORD_99", health_str)
        self.assertNotIn("password", health)
        asyncio.run(close_database())

    def test_production_database_init_failure_fails_closed(self) -> None:
        """Verify database engine initialization failure in PRODUCTION raises RuntimeError."""
        with patch("db.session.create_async_engine", side_effect=Exception("Connection refused")):
            with self.assertRaises(RuntimeError) as ctx:
                initialize_database(self.prod_settings)
            self.assertIn(
                "Database initialization failed in production environment", str(ctx.exception)
            )

    def test_production_redis_init_failure_fails_closed(self) -> None:
        """Verify Redis initialization failure in PRODUCTION raises RuntimeError."""
        with patch("redis.asyncio.Redis", side_effect=Exception("Redis connection refused")):
            with self.assertRaises(RuntimeError) as ctx:
                initialize_redis(self.prod_settings)
            self.assertIn(
                "Redis initialization failed in production environment", str(ctx.exception)
            )

    def test_health_check_does_not_falsely_claim_connected_on_failure(self) -> None:
        """Verify health check returns UNAVAILABLE when database connection fails."""
        initialize_database(self.prod_settings)
        mock_engine = MagicMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.side_effect = Exception("DB Down")
        mock_engine.connect.return_value = mock_cm

        with patch("db.session._async_engine", mock_engine):
            health = asyncio.run(check_database_health(self.prod_settings))
            self.assertEqual(health["status"], "UNAVAILABLE")
            self.assertFalse(health["connected"])
            self.assertIsNotNone(health["error"])
        asyncio.run(close_database())

    def test_redis_health_check_does_not_falsely_claim_connected_on_failure(self) -> None:
        """Verify Redis health check returns UNAVAILABLE when ping fails."""
        initialize_redis(self.prod_settings)
        with patch("db.redis._redis_client.ping", side_effect=Exception("Redis Down")):
            health = asyncio.run(check_redis_health(self.prod_settings))
            self.assertEqual(health["status"], "UNAVAILABLE")
            self.assertFalse(health["connected"])
            self.assertIsNotNone(health["error"])
        asyncio.run(close_redis())


if __name__ == "__main__":
    unittest.main()
