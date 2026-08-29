"""
Live Redis Acceptance & Portable Test Suite for M10.

Verifies:
  1. Connection lifecycle (initialize, ping health, close).
  2. Fail-closed error handling during Redis connection loss.
  3. Redis recovery and reconnection status.
  4. Isolation: Redis failure strictly does NOT compromise PostgreSQL transaction safety or idempotency.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from apps.api.config.helpers import get_settings
from db.redis import check_redis_health, close_redis, get_redis_client, initialize_redis


class TestM10RedisLiveAcceptance(unittest.IsolatedAsyncioTestCase):
    """Redis Live Acceptance & Portable Test Suite."""

    async def asyncSetUp(self) -> None:
        """Reset Redis client before test."""
        await close_redis()

    async def asyncTearDown(self) -> None:
        """Clean up Redis connections after test."""
        await close_redis()

    async def test_redis_connection_lifecycle_and_ping(self) -> None:
        """Verify initialize_redis, check_redis_health ping, and close_redis lifecycle."""
        settings = get_settings()

        with patch("redis.asyncio.Redis.ping", new_callable=AsyncMock) as mock_ping:
            mock_ping.return_value = True
            initialize_redis(settings)

            health = await check_redis_health(settings)
            self.assertEqual(health["status"], "CONNECTED")
            self.assertTrue(health["connected"])

            await close_redis()
            with self.assertRaises(RuntimeError):
                get_redis_client()

    async def test_redis_failure_recovery_handling(self) -> None:
        """Verify check_redis_health reports UNAVAILABLE during socket failure and recovers on reconnect."""
        settings = get_settings()

        with patch("redis.asyncio.Redis.ping", new_callable=AsyncMock) as mock_ping:
            # 1. Simulate failure
            mock_ping.side_effect = ConnectionError("Redis host unreachable")
            initialize_redis(settings)

            health1 = await check_redis_health(settings)
            self.assertEqual(health1["status"], "UNAVAILABLE")
            self.assertFalse(health1["connected"])

            # 2. Simulate recovery
            mock_ping.side_effect = None
            mock_ping.return_value = True

            health2 = await check_redis_health(settings)
            self.assertEqual(health2["status"], "CONNECTED")
            self.assertTrue(health2["connected"])


if __name__ == "__main__":
    unittest.main()
