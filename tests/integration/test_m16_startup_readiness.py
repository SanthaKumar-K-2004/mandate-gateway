"""
Integration tests for M16 Startup Readiness, Migration Detection & Health Endpoints.
"""

import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.app.factory import create_app
from apps.api.app.health import handle_ready_async
from apps.api.config.settings import Settings
from apps.api.deployment.migration_guard import migration_guard
from db.models.base import Base
from db.unit_of_work import AsyncUnitOfWork


class TestM16StartupReadinessIntegration(unittest.IsolatedAsyncioTestCase):
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

    async def test_migration_guard_bootstrapped_tables(self) -> None:
        """Verify MigrationGuard detects bootstrapped database tables in integration environment."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            status = await migration_guard.check_migration_status(uow.session)
            self.assertTrue(status["is_ready"])
            self.assertIn(status["status"], ("UP_TO_DATE", "BOOTSTRAPPED_READY"))

    async def test_readiness_probe_integration(self) -> None:
        """Verify handle_ready_async under integration lifecycle."""
        app = create_app(auto_startup=False)
        settings = Settings.load(host_context=True)
        app.lifecycle.mark_ready()

        status_code, body = await handle_ready_async(app.lifecycle, settings)
        self.assertEqual(status_code, 200)
        self.assertEqual(body["status"], "READY")
        self.assertIn("migration", body["dependencies"])


if __name__ == "__main__":
    unittest.main()
