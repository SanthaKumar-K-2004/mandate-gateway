"""
M13 — Health, Liveness, Readiness & Diagnostics Test Suite
Section S00.4 & M13 — Operational Readiness Foundation
"""

import dataclasses
import unittest
from unittest.mock import AsyncMock, patch

from apps.api.app.health import handle_health, handle_ready_async
from apps.api.app.lifecycle import AppLifecycle
from apps.api.config.helpers import get_settings
from apps.api.config.types import Environment


class TestM13HealthReadiness(unittest.IsolatedAsyncioTestCase):
    """Test suite for /health, /live, /ready, and /diagnostics endpoints."""

    def setUp(self) -> None:
        self.settings = get_settings()
        self.lifecycle = AppLifecycle()

    def test_liveness_health_endpoint_fast_response(self) -> None:
        """Verify /health returns 200 OK instantly without dependency checks."""
        status_code, body = handle_health(self.settings)
        self.assertEqual(status_code, 200)
        self.assertEqual(body["status"], "HEALTHY")
        self.assertNotIn("password", body)
        self.assertNotIn("secret", body)

    async def test_readiness_in_development_mode(self) -> None:
        """Verify /ready returns 200 OK when lifecycle is READY in dev mode."""
        self.lifecycle.startup()
        status_code, body = await handle_ready_async(self.lifecycle, self.settings)
        self.assertEqual(status_code, 200)
        self.assertEqual(body["status"], "READY")

    async def test_readiness_fails_when_uninitialized(self) -> None:
        """Verify /ready returns 503 when lifecycle is BOOTING or INITIALIZING."""
        status_code, body = await handle_ready_async(self.lifecycle, self.settings)
        self.assertEqual(status_code, 503)
        self.assertEqual(body["status"], "NOT_READY")

    @patch("db.session.check_database_health", new_callable=AsyncMock)
    @patch("db.redis.check_redis_health", new_callable=AsyncMock)
    async def test_readiness_in_production_mode_checks_dependencies(
        self, mock_redis: AsyncMock, mock_db: AsyncMock
    ) -> None:
        """Verify /ready in production mode checks DB and Redis health and returns 503 if DB fails."""
        prod_settings = dataclasses.replace(get_settings(), app_env=Environment.PRODUCTION)
        self.lifecycle.startup()

        # Case 1: Both DB and Redis connected
        mock_db.return_value = {"status": "CONNECTED"}
        mock_redis.return_value = {"status": "CONNECTED"}
        status_code, body = await handle_ready_async(self.lifecycle, prod_settings)
        self.assertEqual(status_code, 200)
        self.assertEqual(body["status"], "READY")

        # Case 2: Database UNAVAILABLE
        mock_db.return_value = {"status": "UNAVAILABLE"}
        status_code_fail, body_fail = await handle_ready_async(self.lifecycle, prod_settings)
        self.assertEqual(status_code_fail, 503)
        self.assertEqual(body_fail["status"], "NOT_READY")
        self.assertEqual(body_fail["dependencies"]["database"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
