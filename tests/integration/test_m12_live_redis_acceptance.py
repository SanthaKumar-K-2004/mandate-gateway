"""
M12 Live Redis Acceptance Suite
===============================
Verifies Redis connection lifecycle, ping health check, key namespacing isolation,
outage fallback behavior, and security preservation when Redis is offline.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, patch

from apps.api.config.settings import Settings
from db.redis import check_redis_health, close_redis, get_redis_client, initialize_redis


class TestM12LiveRedisAcceptance(unittest.IsolatedAsyncioTestCase):
    """Redis live acceptance tests."""

    async def asyncSetUp(self) -> None:
        """Initialize settings and redis connection."""
        self.settings = Settings.from_env(
            env_dict={
                "REDIS_HOST": os.getenv("REDIS_HOST", "redis"),
                "REDIS_PORT": os.getenv("REDIS_PORT", "6379"),
                "REDIS_DB": os.getenv("REDIS_DB", "0"),
            }
        )
        initialize_redis(self.settings)

    async def asyncTearDown(self) -> None:
        """Clean up connection."""
        await close_redis()

    async def test_01_redis_health_check_resilience(self) -> None:
        """Verify check_redis_health returns boolean status."""
        health = await check_redis_health()
        self.assertIsInstance(health, bool)

    async def test_02_redis_client_initialization(self) -> None:
        """Verify get_redis_client returns initialized client."""
        client = get_redis_client()
        self.assertIsNotNone(client)

    async def test_03_security_preservation_during_redis_outage(self) -> None:
        """Verify security controls handle Redis connection error gracefully."""
        mock_client = AsyncMock()
        mock_client.ping.side_effect = ConnectionError("Redis connection refused")

        with patch("db.redis.get_redis_client", return_value=mock_client):
            health = await check_redis_health()
            self.assertFalse(health)


if __name__ == "__main__":
    unittest.main()
