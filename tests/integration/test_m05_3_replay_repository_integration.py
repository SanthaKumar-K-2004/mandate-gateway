"""
Integration tests for S05.3.6.2 ReplayRepository against SQLite in-memory database.
"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models.base import Base
from db.repository.merchant_repository import MerchantRepository
from db.repository.replay_repository import ReplayRepository
from db.repository.transaction_repository import TransactionRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestReplayRepositoryIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test suite for ReplayRepository using SQLite in-memory engine."""

    async def asyncSetUp(self) -> None:
        """Set up in-memory SQLite database and repository sessions."""
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self.session = self.session_factory()
        self.merchant_repo = MerchantRepository(self.session)
        self.tx_repo = TransactionRepository(self.session)
        self.replay_repo = ReplayRepository(self.session)

        # Seed merchant & transaction
        await self.merchant_repo.create_merchant("m_rp_1", "Replay Merchant")
        await self.tx_repo.create_transaction(
            transaction_id="tx_rp_1",
            buyer_id="buyer_rp_1",
            merchant_id="m_rp_1",
            mandate_id="man_rp_1",
            amount_paise=100000,
            cart_hash="cart_rp_1",
            idempotency_key="idemp_rp_1",
        )
        await self.session.commit()

    async def asyncTearDown(self) -> None:
        """Close session and dispose engine."""
        await self.session.close()
        await self.engine.dispose()

    async def test_replay_record_persistence_and_duplicate_rejection(self) -> None:
        """Verify replay record persistence, lookup, and duplicate active rejection."""
        fp = "fp_integ_1"
        tx_id = "tx_rp_1"

        # First consumption -> ALLOW (is_replayed = False)
        is_replayed, rec = await self.replay_repo.check_and_record_replay(
            fingerprint=fp,
            transaction_id=tx_id,
            ttl_seconds=86400,
        )
        await self.session.commit()

        self.assertFalse(is_replayed)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.fingerprint, fp)  # type: ignore[union-attr]

        # Verification via lookup
        retrieved = await self.replay_repo.get_replay_record(fp)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.transaction_id, tx_id)  # type: ignore[union-attr]

        # Second consumption attempt -> REJECT (is_replayed = True)
        async with self.session_factory() as session2:
            repo2 = ReplayRepository(session2)
            is_replayed_2, rec_2 = await repo2.check_and_record_replay(
                fingerprint=fp,
                transaction_id=tx_id,
                ttl_seconds=86400,
            )
            self.assertTrue(is_replayed_2)
            self.assertEqual(rec_2.fingerprint, fp)  # type: ignore[union-attr]

    async def test_conflicting_context_rejection(self) -> None:
        """Verify attempting to reuse a fingerprint with conflicting transaction_id raises ValueError."""
        fp = "fp_integ_conflict"

        await self.replay_repo.record_replay_fingerprint(fp, "tx_rp_1")
        await self.session.commit()

        async with self.session_factory() as session2:
            repo2 = ReplayRepository(session2)
            with self.assertRaises(ValueError) as ctx:
                await repo2.check_and_record_replay(
                    fingerprint=fp,
                    transaction_id="tx_rp_attacker",
                )

            self.assertIn("Conflicting context reuse detected", str(ctx.exception))

    async def test_expired_fingerprint_allows_new_replay_record(self) -> None:
        """Verify an expired replay record allows a new registration once TTL expires."""
        fp = "fp_integ_exp"
        past_time = _utc_now() - timedelta(seconds=100000)

        await self.replay_repo.record_replay_fingerprint(fp, "tx_rp_1", created_at=past_time)
        await self.session.commit()

        # Check at current time with TTL=86400 -> Expired -> ALLOW (is_replayed = False)
        async with self.session_factory() as session2:
            repo2 = ReplayRepository(session2)
            is_replayed, new_rec = await repo2.check_and_record_replay(
                fingerprint=fp,
                transaction_id="tx_rp_1",
                ttl_seconds=86400,
                at=_utc_now(),
            )
            await session2.commit()
            self.assertFalse(is_replayed)
            self.assertIsNotNone(new_rec)

    async def test_concurrent_replay_submission(self) -> None:
        """
        Multi-worker concurrency test against SQLite in-memory session factory:
        10 workers concurrently submit identical replay fingerprint.
        Invariant: Exactly 1 worker registers new fingerprint (is_replayed=False),
        9 detect active replay (is_replayed=True).
        """
        fp = "fp_race_1"
        tx_id = "tx_rp_1"

        async def worker_submit(idx: int) -> bool:
            async with self.session_factory() as session_worker:
                repo_w = ReplayRepository(session_worker)
                try:
                    is_replayed, _ = await repo_w.check_and_record_replay(
                        fingerprint=fp,
                        transaction_id=tx_id,
                        ttl_seconds=86400,
                    )
                    await session_worker.commit()
                    return not is_replayed  # True if registered first, False if detected as replay
                except ValueError:
                    await session_worker.rollback()
                    return False

        results = await asyncio.gather(*[worker_submit(i) for i in range(10)])
        registrations = sum(1 for r in results if r is True)
        rejections = sum(1 for r in results if r is False)

        self.assertEqual(registrations, 1)
        self.assertEqual(rejections, 9)


if __name__ == "__main__":
    unittest.main()
