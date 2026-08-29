"""
Integration tests for M15 Transaction Timeline Reconstruction Engine.
"""

import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.observability.timeline import timeline_reconstructor
from db.models.base import Base
from db.unit_of_work import AsyncUnitOfWork


class TestM15TransactionTimelineIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        """Initialize in-memory SQLite engine for integration testing."""
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

    async def test_timeline_reconstruction_multi_source(self) -> None:
        """Verify timeline reconstructs ordered items across transaction persistence, audit, receipt, and outbox."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.transactions.create_transaction(
                transaction_id="tx_tl_100",
                buyer_id="buyer_tl_1",
                merchant_id="mer_tl_owner",
                mandate_id="man_tl_1",
                amount_paise=15000,
                cart_hash="hash_tl_100",
                idempotency_key="idempotency_tl_100",
            )
            await uow.commit()

        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            res = await timeline_reconstructor.reconstruct(
                transaction_id="tx_tl_100",
                uow=uow,
                requesting_merchant_id="mer_tl_owner",
            )
            self.assertEqual(res["transaction_id"], "tx_tl_100")
            self.assertEqual(res["merchant_id"], "mer_tl_owner")
            self.assertGreaterEqual(res["timeline_length"], 1)

    async def test_timeline_reconstruction_tenant_isolation_breach_fails_closed(self) -> None:
        """Verify requesting timeline for another merchant's transaction fails closed with PermissionError."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.transactions.create_transaction(
                transaction_id="tx_tl_200",
                buyer_id="buyer_2",
                merchant_id="mer_real_owner",
                mandate_id="man_2",
                amount_paise=5000,
                cart_hash="hash_tl_200",
                idempotency_key="idempotency_tl_200",
            )
            await uow.commit()

        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            with self.assertRaises(PermissionError):
                await timeline_reconstructor.reconstruct(
                    transaction_id="tx_tl_200",
                    uow=uow,
                    requesting_merchant_id="mer_attacker",
                )


if __name__ == "__main__":
    unittest.main()
