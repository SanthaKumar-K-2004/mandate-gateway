"""
Mandate Gateway — Milestone M18 Concurrency Tests
Workstream H — Multi-Threaded Concurrent Operations & Demo Journey Execution
"""

import asyncio
import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import db.session
from db.models.base import Base


class TestM18UIConcurrency(unittest.IsolatedAsyncioTestCase):

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

    async def test_concurrent_demo_journeys(self) -> None:
        from apps.api.routers.operations import execute_demo_journey_endpoint

        # Execute 5 concurrent demo payment journeys simultaneously
        tasks = [execute_demo_journey_endpoint(operator={"role": "operator"}) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        self.assertEqual(len(results), 5)
        tx_ids = [r["transaction_id"] for r in results]
        self.assertEqual(len(set(tx_ids)), 5)  # 5 unique transaction IDs created

        for r in results:
            self.assertEqual(r["status"], "SUCCESS")
            self.assertEqual(r["state"], "COMMITTED")


if __name__ == "__main__":
    unittest.main()
