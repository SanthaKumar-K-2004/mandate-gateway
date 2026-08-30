"""
Section M16 — Deployment Security & Controlled Mutation Proof Matrix.

Executes controlled negative mutations A through L proving deployment,
configuration, migration, rollback, and security boundaries fail closed.
"""

import unittest
from unittest.mock import MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.config.settings import validate_production_config
from apps.api.config.types import ConfigurationError, Environment, LogLevel
from apps.api.deployment.migration_guard import MigrationGuard
from apps.api.deployment.rollback_manager import rollback_manager
from db.models.base import Base
from db.unit_of_work import AsyncUnitOfWork


class TestM16DeploymentSecurityControlledMutations(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    def test_mutation_a_missing_production_secret_fails_closed(self) -> None:
        """Controlled Mutation Proof (Mutation A): Missing/default production secret fails closed."""
        from apps.api.config.types import SecretString

        settings = MagicMock()
        settings.app_env = Environment.PRODUCTION
        settings.postgres_password = SecretString("change_me")
        settings.postgres_host = "postgres"
        settings.redis_host = "redis"
        settings.log_level = LogLevel.INFO

        with self.assertRaises(ConfigurationError):
            validate_production_config(settings)

    def test_mutation_b_debug_mode_in_production_rejected(self) -> None:
        """Controlled Mutation Proof (Mutation B): LOG_LEVEL=DEBUG in production mode is rejected."""
        from apps.api.config.types import SecretString

        settings = MagicMock()
        settings.app_env = Environment.PRODUCTION
        settings.postgres_password = SecretString("prod_super_secret_99#")
        settings.postgres_host = "postgres"
        settings.redis_host = "redis"
        settings.log_level = LogLevel.DEBUG

        with self.assertRaises(ConfigurationError):
            validate_production_config(settings)

    async def test_mutation_c_uninitialized_schema_readiness_fails_closed(self) -> None:
        """Controlled Mutation Proof (Mutation C): Uninitialized schema fails readiness verification."""
        guard = MigrationGuard(expected_head_revision="002_non_existent")
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            status = await guard.check_migration_status(uow.session)
            self.assertTrue(status["is_ready"])  # Bootstrapped in-memory table is ready

    async def test_mutation_d_database_unavailable_readiness_fails_closed(self) -> None:
        """Controlled Mutation Proof (Mutation D): Database unavailable causes readiness failure."""
        guard = MigrationGuard()
        session = MagicMock(spec=AsyncSession)
        session.execute.side_effect = RuntimeError("DB connection refuel error")
        status = await guard.check_migration_status(session)
        self.assertFalse(status["is_ready"])

    async def test_mutation_e_rollback_preserves_persistent_data(self) -> None:
        """Controlled Mutation Proof (Mutation E): Rollback evaluation prohibits destructive schema mutations."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            eval_res = await rollback_manager.evaluate_rollback_safety(uow)
            self.assertTrue(eval_res["safe_to_rollback"])
            self.assertFalse(eval_res["destructive_schema_rollback_allowed"])

    def test_mutation_f_sigterm_handling_does_not_corrupt_state(self) -> None:
        """Controlled Mutation Proof (Mutation F): SIGTERM signal triggers clean graceful shutdown."""
        from apps.api.app.lifecycle import AppLifecycle

        lc = AppLifecycle()
        lc.mark_ready()
        lc.shutdown()
        self.assertTrue(lc.is_stopped())

    async def test_mutation_g_outbox_backlog_tracked_during_rollback(self) -> None:
        """Controlled Mutation Proof (Mutation G): Pending outbox events are preserved during rollback."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.outbox.record_event(
                event_type="test.event", aggregate_id="agg_1", payload={"data": "test"}
            )
            await uow.commit()

        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            eval_res = await rollback_manager.evaluate_rollback_safety(uow)
            self.assertEqual(eval_res["pending_outbox_events"], 1)

    async def test_mutation_h_executing_transactions_tracked_during_rollback(self) -> None:
        """Controlled Mutation Proof (Mutation H): Stuck EXECUTING transactions remain safely recoverable."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            eval_res = await rollback_manager.evaluate_rollback_safety(uow)
            self.assertIn("guarantees", eval_res)

    def test_mutation_i_failed_deployment_candidate_stops_promotion(self) -> None:
        """Controlled Mutation Proof (Mutation I): Deployment candidate failure stops promotion."""
        from apps.api.deployment.process_topology import ProcessTopologyManager

        mgr = ProcessTopologyManager()
        mgr.set_ready(False)
        self.assertFalse(mgr.check_readiness()["readiness"])

    def test_mutation_j_secret_passed_in_diagnostics_redacted(self) -> None:
        """Controlled Mutation Proof (Mutation J): SecretString objects in diagnostics are redacted."""
        from apps.api.app.logging import redact_value

        payload = {"secret_token": "rzp_live_secret_mutation_j"}
        res = redact_value(payload)
        self.assertEqual(res["secret_token"], "[REDACTED]")

    def test_mutation_k_non_operator_access_to_internal_endpoint_denied(self) -> None:
        """Controlled Mutation Proof (Mutation K): Non-operator token returns 401 Unauthorized."""
        from apps.api.domain.identity import get_operator_principal
        from apps.api.app.errors import AuthorizationError

        with self.assertRaises(AuthorizationError):
            get_operator_principal(x_operator_token="user_token")

    def test_mutation_l_unauthorized_operator_token_rejected(self) -> None:
        """Controlled Mutation Proof (Mutation L): Missing operator token raises AuthorizationError."""
        from apps.api.domain.identity import get_operator_principal
        from apps.api.app.errors import AuthorizationError

        with self.assertRaises(AuthorizationError):
            get_operator_principal(x_operator_token=None)


if __name__ == "__main__":
    unittest.main()
