"""
Mandate Gateway — Milestone M18 Production Release Certification
Workstream H & I — Production Product Acceptance Suite
"""

import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import db.session
from db.models.base import Base
from apps.api.app.factory import MandateGatewayApp


class TestM18ProductAcceptance(unittest.IsolatedAsyncioTestCase):

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
        db.session._async_session_factory = self.session_factory
        self.app = MandateGatewayApp()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        db.session._async_session_factory = None

    async def test_full_m18_product_acceptance_lifecycle(self) -> None:
        from apps.api.routers.operations import (
            execute_demo_journey_endpoint,
            get_operations_summary_endpoint,
            verify_audit_chain_endpoint,
        )

        # 1. Verify initial summary
        summary = await get_operations_summary_endpoint(operator={"role": "operator"})
        self.assertEqual(summary["status"], "OPERATIONAL")

        # 2. Run E2E Payment Journey
        journey = await execute_demo_journey_endpoint(operator={"role": "operator"})
        self.assertEqual(journey["status"], "SUCCESS")

        # 3. Verify Audit Chain
        audit_res = await verify_audit_chain_endpoint(operator={"role": "operator"})
        self.assertTrue(audit_res["is_valid"])


if __name__ == "__main__":
    unittest.main()
