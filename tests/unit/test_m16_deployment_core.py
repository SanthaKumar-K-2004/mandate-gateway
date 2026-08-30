"""
Unit tests for M16 Production Deployment Core Components.
"""

import unittest
from unittest.mock import MagicMock, AsyncMock

from apps.api.config.settings import validate_production_config
from apps.api.config.types import ConfigurationError, Environment, LogLevel
from apps.api.deployment.migration_guard import MigrationGuard, KNOWN_HEAD_REVISION
from apps.api.deployment.process_topology import ProcessTopologyManager, ProcessRole


class TestM16DeploymentCoreUnit(unittest.TestCase):
    def test_process_topology_manager(self) -> None:
        """Verify ProcessTopologyManager metadata, liveness, and readiness indicators."""
        mgr = ProcessTopologyManager(role=ProcessRole.OUTBOX_WORKER)
        meta = mgr.get_process_metadata()
        self.assertEqual(meta["role"], "outbox_worker")
        self.assertTrue(meta["is_outbox_worker"])
        self.assertFalse(meta["handles_http_traffic"])

        mgr.set_alive(True)
        mgr.set_ready(True)
        self.assertTrue(mgr.check_liveness()["liveness"])
        self.assertTrue(mgr.check_readiness()["readiness"])

    def test_validate_production_config_insecure_password_raises(self) -> None:
        """Verify production config validation rejects default postgres passwords."""
        from apps.api.config.types import SecretString

        settings = MagicMock()
        settings.app_env = Environment.PRODUCTION
        settings.postgres_password = SecretString("postgres")
        settings.postgres_host = "postgres"
        settings.redis_host = "redis"
        settings.log_level = LogLevel.INFO

        with self.assertRaises(ConfigurationError):
            validate_production_config(settings)

    def test_validate_production_config_debug_level_raises(self) -> None:
        """Verify production config validation rejects LOG_LEVEL=DEBUG."""
        from apps.api.config.types import SecretString

        settings = MagicMock()
        settings.app_env = Environment.PRODUCTION
        settings.postgres_password = SecretString("secure_prod_pass_99#")
        settings.postgres_host = "postgres"
        settings.redis_host = "redis"
        settings.log_level = LogLevel.DEBUG

        with self.assertRaises(ConfigurationError):
            validate_production_config(settings)


class TestM16MigrationGuardUnit(unittest.IsolatedAsyncioTestCase):
    async def test_migration_guard_up_to_date(self) -> None:
        """Verify MigrationGuard returns UP_TO_DATE when revision matches."""
        guard = MigrationGuard(expected_head_revision=KNOWN_HEAD_REVISION)
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (KNOWN_HEAD_REVISION,)
        session.execute.return_value = mock_result

        status = await guard.check_migration_status(session)
        self.assertEqual(status["status"], "UP_TO_DATE")
        self.assertTrue(status["is_ready"])


if __name__ == "__main__":
    unittest.main()
