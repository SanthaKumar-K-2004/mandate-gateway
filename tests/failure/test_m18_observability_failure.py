"""
Mandate Gateway — Milestone M18 Failure Injection Tests
Workstream H — Observability & Operations Failure Resilience
"""

import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import db.session
from db.models.base import Base


class TestM18ObservabilityFailure(unittest.IsolatedAsyncioTestCase):

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

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        db.session._async_session_factory = None

    async def test_audit_verify_failure_resilience(self) -> None:
        from apps.api.routers.operations import verify_audit_chain_endpoint

        res = await verify_audit_chain_endpoint(operator={"role": "operator"})
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["status"], "VERIFIED")

    async def test_receipt_verify_format_resilience(self) -> None:
        from apps.api.routers.operations import verify_action_receipt_endpoint

        # Invalid short signature
        res = verify_action_receipt_endpoint(
            payload_hash="hash", signature_hex="short", operator={"role": "operator"}
        )
        self.assertFalse(res["is_valid"])


if __name__ == "__main__":
    unittest.main()
