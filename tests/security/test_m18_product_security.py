"""
Mandate Gateway — Milestone M18 Security Tests
Workstream G — Product Security, Operator Auth, Tenant Isolation & Secret Redaction
"""

import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import db.session
from db.models.base import Base
from apps.api.app.factory import MandateGatewayApp


class TestM18ProductSecurity(unittest.IsolatedAsyncioTestCase):

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

    async def test_unauthorized_operator_access_rejected(self) -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/internal/operations/security/summary",
            "headers": [(b"authorization", b"Bearer unauthorized_token_999")],
        }

        async def receive() -> dict:
            return {"type": "http.request"}

        response_status = None

        async def send(message: dict) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]

        await self.app(scope, receive, send)
        self.assertEqual(response_status, 401)

    async def test_authorized_operator_access_granted(self) -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/internal/operations/security/summary",
            "headers": [(b"authorization", b"Bearer rzp_live_operator_token_123")],
        }

        async def receive() -> dict:
            return {"type": "http.request"}

        response_status = None

        async def send(message: dict) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]

        await self.app(scope, receive, send)
        self.assertEqual(response_status, 200)

    async def test_tenant_isolation_forbidden(self) -> None:
        from apps.api.observability.investigation import investigator

        investigator.register_transaction(
            "tx_demo_100",
            {
                "transaction_id": "tx_demo_100",
                "merchant_id": "mer_owner_100",
                "buyer_id": "buy_user_100",
                "mandate_id": "man_100",
                "state": "COMMITTED",
            },
        )

        with self.assertRaises(PermissionError):
            investigator.investigate("tx_demo_100", requesting_merchant_id="unauthorized_merchant")


if __name__ == "__main__":
    unittest.main()
