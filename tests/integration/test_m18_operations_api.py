"""
Mandate Gateway — Milestone M18 Integration Tests
Workstream D & F — Operations API & Live Payment Demo Journey
"""

import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import db.session
from db.models.base import Base
from apps.api.app.factory import MandateGatewayApp
from db.unit_of_work import AsyncUnitOfWork


class TestM18OperationsAPI(unittest.IsolatedAsyncioTestCase):

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

    async def test_dashboard_ui_endpoint(self) -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/dashboard",
            "headers": [],
        }

        async def receive() -> dict:
            return {"type": "http.request"}

        response_status = None
        response_body = b""

        async def send(message: dict) -> None:
            nonlocal response_status, response_body
            if message["type"] == "http.response.start":
                response_status = message["status"]
            elif message["type"] == "http.response.body":
                response_body += message.get("body", b"")

        await self.app(scope, receive, send)
        self.assertEqual(response_status, 200)
        self.assertIn(b"RAZERPAY", response_body)
        self.assertIn(b"Executive Operations Dashboard", response_body)

    async def test_demo_journey_execution(self) -> None:
        from apps.api.routers.operations import execute_demo_journey_endpoint

        res = await execute_demo_journey_endpoint(operator={"role": "operator"})
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["transaction_id"].startswith("tx_demo_"))
        self.assertEqual(res["state"], "COMMITTED")

        # Verify transaction persisted in unit of work
        async with AsyncUnitOfWork() as uow:
            tx = await uow.transactions.get_transaction(res["transaction_id"])
            self.assertIsNotNone(tx)
            assert tx is not None
            self.assertEqual(tx.amount_paise, 25000)

    async def test_operations_summary(self) -> None:
        from apps.api.routers.operations import get_operations_summary_endpoint

        res = await get_operations_summary_endpoint(operator={"role": "operator"})
        self.assertEqual(res["status"], "OPERATIONAL")
        self.assertTrue(res["audit_chain_valid"])

    async def test_audit_chain_verification_endpoint(self) -> None:
        from apps.api.routers.operations import verify_audit_chain_endpoint

        res = await verify_audit_chain_endpoint(operator={"role": "operator"})
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
