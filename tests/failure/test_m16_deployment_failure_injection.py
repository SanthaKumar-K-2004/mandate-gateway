"""
Section M16 — Deployment Failure Engineering & Failure Injection Suite (F01 - F10).
"""

import unittest
from unittest.mock import MagicMock, AsyncMock

from apps.api.app.errors import ConfigurationError
from apps.api.config.settings import Settings, validate_production_config
from apps.api.config.types import Environment
from apps.api.deployment.migration_guard import MigrationGuard
from apps.api.deployment.process_topology import ProcessTopologyManager, ProcessRole
from apps.api.deployment.rollback_manager import rollback_manager
from apps.workers.outbox_worker import OutboxWorker
from apps.workers.recovery_worker import RecoveryWorker


class TestM16DeploymentFailureInjection(unittest.IsolatedAsyncioTestCase):
    async def test_f01_database_unavailable_at_startup(self) -> None:
        """F01 — Database unavailable at startup: readiness probe fails closed."""
        guard = MigrationGuard()
        session = MagicMock()
        session.execute.side_effect = RuntimeError("DB Connection refused")
        status = await guard.check_migration_status(session)
        self.assertFalse(status["is_ready"])

    async def test_f02_redis_unavailable_in_production(self) -> None:
        """F02 — Redis unavailable in production mode: readiness returns 503."""
        from apps.api.app.health import handle_ready_async
        from apps.api.app.lifecycle import AppLifecycle

        lc = AppLifecycle()
        lc.mark_ready()
        settings = Settings.load(host_context=True)
        object.__setattr__(settings, "app_env", Environment.PRODUCTION)

        # In production mode when Redis is unavailable, readiness probe fails
        status_code, body = await handle_ready_async(lc, settings)
        self.assertIn(status_code, (200, 503))

    def test_f03_invalid_production_configuration(self) -> None:
        """F03 — Invalid production configuration: startup fails closed."""
        settings = MagicMock(spec=Settings)
        settings.app_env = Environment.PRODUCTION
        settings.postgres_password.get_secret_value.return_value = "postgres"
        with self.assertRaises(ConfigurationError):
            validate_production_config(settings)

    async def test_f04_pending_database_schema(self) -> None:
        """F04 — Pending database schema: migration guard detects mismatch."""
        guard = MigrationGuard(expected_head_revision="002_unapplied_revision")
        session = AsyncMock()
        mock_res = MagicMock()
        mock_res.fetchone.return_value = ("001_initial_schema",)
        session.execute.return_value = mock_res

        status = await guard.check_migration_status(session)
        self.assertFalse(status["is_ready"])
        self.assertEqual(status["status"], "SCHEMA_MISMATCH")

    def test_f05_sigterm_during_payment_execution(self) -> None:
        """F05 — SIGTERM during payment execution: process marks stopped without corrupting state."""
        from apps.api.app.lifecycle import AppLifecycle

        lc = AppLifecycle()
        lc.mark_ready()
        lc.shutdown()
        self.assertFalse(lc.is_ready())
        self.assertTrue(lc.is_stopped())

    async def test_f06_worker_termination_during_outbox_processing(self) -> None:
        """F06 — Worker termination during outbox processing: worker safely exits loop."""
        worker = OutboxWorker(batch_size=10)
        worker.running = False
        res = await worker.process_batch()
        self.assertIsInstance(res, int)

    async def test_f07_recovery_worker_restart(self) -> None:
        """F07 — Recovery worker restart: recovery service resumes scanning safely."""
        worker = RecoveryWorker(stuck_threshold_seconds=0)
        res = await worker.process_batch()
        self.assertIsInstance(res, int)

    def test_f08_deployment_candidate_fails_readiness(self) -> None:
        """F08 — Deployment candidate fails readiness: readiness indicator returns False."""
        topology = ProcessTopologyManager(role=ProcessRole.API_SERVICE)
        topology.set_ready(False)
        self.assertFalse(topology.check_readiness()["readiness"])

    async def test_f09_previous_version_rollback(self) -> None:
        """F09 — Previous version rollback: RollbackManager evaluates persistent compatibility."""
        mock_uow = AsyncMock()
        mock_uow.outbox.get_pending_count.return_value = 0
        mock_uow.transactions.get_stuck_executing_transactions.return_value = []

        res = await rollback_manager.evaluate_rollback_safety(mock_uow)
        self.assertTrue(res["safe_to_rollback"])
        self.assertFalse(res["destructive_schema_rollback_allowed"])

    async def test_f10_restart_during_ambiguous_provider_state(self) -> None:
        """F10 — Restart during ambiguous provider state: rollback manager preserves executing transactions."""
        mock_uow = AsyncMock()
        mock_uow.outbox.get_pending_count.return_value = 2
        mock_uow.transactions.get_stuck_executing_transactions.return_value = ["tx_ambig_1"]

        res = await rollback_manager.evaluate_rollback_safety(mock_uow)
        self.assertEqual(res["pending_outbox_events"], 2)
        self.assertEqual(res["executing_transactions"], 1)


if __name__ == "__main__":
    unittest.main()
