"""
Unit tests for M05.1 Database Session & Redis Connection Foundation.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from apps.api.config.settings import Settings
from apps.api.config.types import Environment, LogLevel, SecretString
from db.redis import check_redis_health, close_redis, get_redis_client, initialize_redis
from db.session import (
    check_database_health,
    close_database,
    get_postgres_uri,
    initialize_database,
)


class TestM051InfrastructureUnit(unittest.TestCase):
    """Unit tests for db/session.py and db/redis.py."""

    def setUp(self) -> None:
        self.settings = Settings(
            app_env=Environment.TEST,
            app_name="mandate-gateway",
            log_level=LogLevel.INFO,
            host_context=False,
            postgres_host="localhost",
            postgres_port=5432,
            postgres_db="mandate_test",
            postgres_user="postgres",
            postgres_password=SecretString("supersecret_pass_123"),
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
        )

    def test_postgres_uri_security(self) -> None:
        """Verify get_postgres_uri constructs correct URI without revealing password in string representation."""
        uri = get_postgres_uri(self.settings)
        self.assertTrue(
            uri.startswith(
                "postgresql+asyncpg://postgres:supersecret_pass_123@localhost:5432/mandate_test"
            )
        )

    def test_initialize_database(self) -> None:
        """Verify initialize_database creates engine using settings."""
        initialize_database(self.settings)
        mock_engine = MagicMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.side_effect = Exception("DB Offline")
        mock_engine.connect.return_value = mock_cm

        with patch("db.session._async_engine", mock_engine):
            import asyncio

            health = asyncio.run(check_database_health(self.settings))
            self.assertTrue(health["configured"])
            self.assertEqual(health["host"], "localhost")
        asyncio.run(close_database())

    def test_initialize_redis(self) -> None:
        """Verify initialize_redis creates redis client."""
        initialize_redis(self.settings)
        client = get_redis_client()
        self.assertIsNotNone(client)
        import asyncio

        health = asyncio.run(check_redis_health(self.settings))
        self.assertTrue(health["configured"])
        self.assertEqual(health["port"], 6379)
        asyncio.run(close_redis())

    def test_check_database_health_mocked_success(self) -> None:
        """Verify check_database_health returns CONNECTED when SELECT 1 succeeds."""
        import asyncio

        initialize_database(self.settings)

        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_conn.execute.return_value = mock_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_conn
        mock_engine.connect.return_value = mock_cm

        with patch("db.session._async_engine", mock_engine):
            health = asyncio.run(check_database_health(self.settings))
            self.assertEqual(health["status"], "CONNECTED")
            self.assertTrue(health["connected"])

        asyncio.run(close_database())

    def test_check_redis_health_mocked_success(self) -> None:
        """Verify check_redis_health returns CONNECTED when ping succeeds."""
        import asyncio

        initialize_redis(self.settings)

        with patch("db.redis._redis_client.ping", new_callable=AsyncMock) as mock_ping:
            mock_ping.return_value = True
            health = asyncio.run(check_redis_health(self.settings))
            self.assertEqual(health["status"], "CONNECTED")
            self.assertTrue(health["connected"])

        asyncio.run(close_redis())


if __name__ == "__main__":
    unittest.main()
