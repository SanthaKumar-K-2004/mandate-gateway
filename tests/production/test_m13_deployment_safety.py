"""
M13 — Deployment Preflight Validation & Graceful Shutdown Test Suite
Section M13 — Deployment Safety Foundation
"""

import unittest

from apps.api.app.factory import MandateGatewayApp, validate_preflight_config
from apps.api.app.lifecycle import AppLifecycle, LifecycleState
from apps.api.config.helpers import get_settings


class TestM13DeploymentSafety(unittest.TestCase):
    """Test suite for deployment preflight validation and graceful shutdown."""

    def test_validate_preflight_config_success(self) -> None:
        """Verify preflight config validation passes with valid settings."""
        settings = get_settings()
        result = validate_preflight_config(settings)
        self.assertTrue(result)

    def test_lifecycle_startup_and_shutdown_sequence(self) -> None:
        """Verify lifecycle transitions through BOOTING -> INITIALIZING -> READY -> SHUTTING_DOWN -> STOPPED."""
        lifecycle = AppLifecycle()
        self.assertEqual(lifecycle.state, LifecycleState.BOOTING)

        startup_executed = False
        shutdown_executed = False

        def startup_hook() -> None:
            nonlocal startup_executed
            startup_executed = True

        def shutdown_hook() -> None:
            nonlocal shutdown_executed
            shutdown_executed = True

        lifecycle.add_startup_hook(startup_hook)
        lifecycle.add_shutdown_hook(shutdown_hook)

        lifecycle.startup()
        self.assertTrue(startup_executed)
        self.assertEqual(lifecycle.state, LifecycleState.READY)
        self.assertTrue(lifecycle.is_ready())

        lifecycle.shutdown()
        self.assertTrue(shutdown_executed)
        self.assertEqual(lifecycle.state, LifecycleState.STOPPED)
        self.assertFalse(lifecycle.is_ready())

    def test_app_startup_and_shutdown(self) -> None:
        """Verify MandateGatewayApp instance executes startup and shutdown cleanly."""
        settings = get_settings()
        app = MandateGatewayApp(settings=settings)
        app.startup()
        self.assertEqual(app.lifecycle.state, LifecycleState.READY)

        app.shutdown()
        self.assertEqual(app.lifecycle.state, LifecycleState.STOPPED)


if __name__ == "__main__":
    unittest.main()
