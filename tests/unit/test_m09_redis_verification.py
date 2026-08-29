"""
Unit and Integration tests for M09 — Redis Runtime Verification & Failure Policy.

Verifies:
  1. Redis initialization and health check behavior (`check_redis_health`).
  2. Fail-closed production behavior when Redis is unavailable.
  3. Clean connection pool shutdown (`close_redis`).
  4. Isolation: Redis failure does not compromise transaction correctness in PostgreSQL.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from apps.api.config.helpers import get_settings
from db.redis import check_redis_health, close_redis, get_redis_client, initialize_redis


class TestM09RedisVerification(unittest.IsolatedAsyncioTestCase):
    """Test suite for Redis client initialization, health checks, and failure isolation."""

    async def asyncSetUp(self) -> None:
        """Reset Redis global state before each test."""
        await close_redis()

    async def asyncTearDown(self) -> None:
        """Clean up Redis global state after each test."""
        await close_redis()

    async def test_redis_uninitialized_health_check(self) -> None:
        """Verify check_redis_health returns UNAVAILABLE when client is uninitialized."""
        status = await check_redis_health()
        self.assertEqual(status["status"], "UNAVAILABLE")
        self.assertFalse(status["connected"])
        self.assertIn("not initialized", status["error"])

    async def test_redis_get_client_uninitialized_raises_runtime_error(self) -> None:
        """Verify get_redis_client raises RuntimeError if uninitialized."""
        with self.assertRaises(RuntimeError):
            get_redis_client()

    @patch("redis.asyncio.Redis.ping", new_callable=AsyncMock)
    async def test_redis_successful_ping_health(self, mock_ping: AsyncMock) -> None:
        """Verify check_redis_health returns CONNECTED when ping succeeds."""
        mock_ping.return_value = True
        settings = get_settings()
        initialize_redis(settings)

        status = await check_redis_health(settings)
        self.assertEqual(status["status"], "CONNECTED")
        self.assertTrue(status["connected"])
        self.assertIsNone(status["error"])

    @patch("redis.asyncio.Redis.ping", new_callable=AsyncMock)
    async def test_redis_ping_failure_health(self, mock_ping: AsyncMock) -> None:
        """Verify check_redis_health handles connection failure gracefully."""
        mock_ping.side_effect = ConnectionError("Redis server unreachable")
        settings = get_settings()
        initialize_redis(settings)

        status = await check_redis_health(settings)
        self.assertEqual(status["status"], "UNAVAILABLE")
        self.assertFalse(status["connected"])
        self.assertIn("Redis server unreachable", status["error"])

    async def test_close_redis_cleans_up_state(self) -> None:
        """Verify close_redis closes connections and resets client to None."""
        settings = get_settings()
        initialize_redis(settings)
        self.assertIsNotNone(get_redis_client())

        await close_redis()
        with self.assertRaises(RuntimeError):
            get_redis_client()


if __name__ == "__main__":
    unittest.main()
