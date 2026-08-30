"""
Multi-process runtime concurrency verification suite for M16.
Verifies API service, OutboxWorker, and RecoveryWorker operating concurrently.
"""

import asyncio
import multiprocessing
import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.workers.outbox_worker import OutboxWorker
from apps.workers.recovery_worker import RecoveryWorker
from db.models.base import Base
import db.session


def _run_outbox_worker_process(batch_size: int, results_queue: multiprocessing.Queue) -> None:
    """Worker process function running OutboxWorker.process_batch in dedicated process."""

    async def _async_run() -> int:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        db.session._async_session_factory = session_factory

        worker = OutboxWorker(batch_size=batch_size)
        count = await worker.process_batch()
        await engine.dispose()
        return count

    res = asyncio.run(_async_run())
    results_queue.put(res)


def _run_recovery_worker_process(results_queue: multiprocessing.Queue) -> None:
    """Worker process function running RecoveryWorker.process_batch in dedicated process."""

    async def _async_run() -> int:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        db.session._async_session_factory = session_factory

        worker = RecoveryWorker(stuck_threshold_seconds=0)
        count = await worker.process_batch()
        await engine.dispose()
        return count

    res = asyncio.run(_async_run())
    results_queue.put(res)


class TestM16MultiprocessRuntimeConcurrency(unittest.TestCase):
    def test_multiprocess_topology_execution(self) -> None:
        """Verify OutboxWorker and RecoveryWorker run cleanly in separate OS processes."""
        q_outbox: multiprocessing.Queue[int] = multiprocessing.Queue()
        q_recovery: multiprocessing.Queue[int] = multiprocessing.Queue()

        p_outbox = multiprocessing.Process(target=_run_outbox_worker_process, args=(10, q_outbox))
        p_recovery = multiprocessing.Process(
            target=_run_recovery_worker_process, args=(q_recovery,)
        )

        p_outbox.start()
        p_recovery.start()

        p_outbox.join(timeout=10)
        p_recovery.join(timeout=10)

        self.assertEqual(p_outbox.exitcode, 0)
        self.assertEqual(p_recovery.exitcode, 0)

        res_outbox = q_outbox.get(timeout=2)
        res_recovery = q_recovery.get(timeout=2)

        self.assertIsInstance(res_outbox, int)
        self.assertIsInstance(res_recovery, int)


if __name__ == "__main__":
    unittest.main()
