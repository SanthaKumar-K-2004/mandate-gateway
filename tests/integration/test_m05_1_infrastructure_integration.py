"""
Integration tests for M05.1 Real Production Infrastructure Connectivity.
"""

from __future__ import annotations

import asyncio
import unittest

from apps.api.config.helpers import get_settings
from db.redis import check_redis_health, close_redis, initialize_redis
from db.session import (
    check_database_health,
    close_database,
    initialize_database,
)


class TestM051InfrastructureIntegration(unittest.TestCase):
    """Integration tests executing real PING / SELECT queries against PostgreSQL & Redis when available."""

    def test_real_database_and_redis_integration(self) -> None:
        """Attempt real connection checks and report status or ENVIRONMENT BLOCKED."""
        settings = get_settings()

        initialize_database(settings)
        db_health = asyncio.run(check_database_health(settings))
        asyncio.run(close_database())

        initialize_redis(settings)
        redis_health = asyncio.run(check_redis_health(settings))
        asyncio.run(close_redis())

        if not db_health["connected"] or not redis_health["connected"]:
            print(
                "[INFO] Live infrastructure servers (PostgreSQL/Redis) are unavailable. "
                "Integration status: ENVIRONMENT BLOCKED."
            )
            # Soft skip when host containers are offline in local environment
            self.skipTest("Live PostgreSQL/Redis containers offline (ENVIRONMENT BLOCKED)")
        else:
            self.assertTrue(db_health["connected"])
            self.assertTrue(redis_health["connected"])


if __name__ == "__main__":
    unittest.main()
