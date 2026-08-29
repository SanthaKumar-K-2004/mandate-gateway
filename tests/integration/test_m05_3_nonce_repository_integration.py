"""
Integration tests for S05.3.6.3 NonceRepository against SQLite in-memory database.
"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.domain.types import NonceState
from db.models.base import Base
from db.repository.merchant_repository import MerchantRepository
from db.repository.nonce_repository import NonceRepository
from db.repository.transaction_repository import TransactionRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestNonceRepositoryIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test suite for NonceRepository using SQLite in-memory engine."""

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
        self.nonce_repo = NonceRepository(self.session)

        # Seed merchant & transaction
        await self.merchant_repo.create_merchant("m_nc_1", "Nonce Merchant")
        await self.tx_repo.create_transaction(
            transaction_id="tx_nc_1",
            buyer_id="buyer_nc_1",
            merchant_id="m_nc_1",
            mandate_id="man_nc_1",
            amount_paise=250000,
            cart_hash="cart_nc_1",
            idempotency_key="idemp_nc_1",
        )
        await self.session.commit()

    async def asyncTearDown(self) -> None:
        """Close session and dispose engine."""
        await self.session.close()
        await self.engine.dispose()

    async def test_nonce_creation_lookup_and_single_use_consumption(self) -> None:
        """Verify nonce creation, lookup, valid consumption, and double-consumption rejection."""
        n_val = "n_integ_1"
        tx_id = "tx_nc_1"
        man_id = "man_nc_1"

        # Create ISSUED nonce
        rec = await self.nonce_repo.create_nonce(n_val, tx_id, man_id)
        await self.session.commit()
        self.assertEqual(rec.status, NonceState.ISSUED.value)

        # Consume nonce
        consumed = await self.nonce_repo.consume_nonce(n_val, tx_id, man_id, ttl_seconds=300)
        await self.session.commit()
        self.assertEqual(consumed.status, NonceState.CONSUMED.value)
        self.assertIsNotNone(consumed.consumed_at)

        # Verify consumed status persists across new session
        async with self.session_factory() as session2:
            repo2 = NonceRepository(session2)
            n_check = await repo2.get_nonce(n_val)
            self.assertIsNotNone(n_check)
            self.assertEqual(n_check.status, NonceState.CONSUMED.value)  # type: ignore[union-attr]

            # Second consumption attempt must fail closed
            with self.assertRaises(ValueError) as ctx:
                await repo2.consume_nonce(n_val, tx_id, man_id, ttl_seconds=300)
            self.assertIn("already been consumed", str(ctx.exception))

    async def test_expired_nonce_consumption_rejection(self) -> None:
        """Verify consuming an expired nonce fails closed."""
        n_val = "n_integ_exp"
        tx_id = "tx_nc_1"
        man_id = "man_nc_1"
        past_time = _utc_now() - timedelta(seconds=600)

        await self.nonce_repo.create_nonce(n_val, tx_id, man_id, created_at=past_time)
        await self.session.commit()

        with self.assertRaises(ValueError) as ctx:
            await self.nonce_repo.consume_nonce(n_val, tx_id, man_id, ttl_seconds=300)

        self.assertIn("expired", str(ctx.exception))

    async def test_context_substitution_rejection(self) -> None:
        """Verify consuming nonce with mismatched transaction or mandate ID fails closed."""
        n_val = "n_integ_sub"

        await self.nonce_repo.create_nonce(n_val, "tx_nc_1", "man_nc_1")
        await self.session.commit()

        # Mismatched transaction ID
        with self.assertRaises(ValueError) as ctx_tx:
            await self.nonce_repo.consume_nonce(n_val, "tx_attacker", "man_nc_1")
        self.assertIn("Nonce context mismatch", str(ctx_tx.exception))

        # Mismatched mandate ID
        with self.assertRaises(ValueError) as ctx_man:
            await self.nonce_repo.consume_nonce(n_val, "tx_nc_1", "man_attacker")
        self.assertIn("Nonce context mismatch", str(ctx_man.exception))

    async def test_concurrent_nonce_consumption_exact_once(self) -> None:
        """
        Multi-worker concurrency test against SQLite in-memory session factory:
        10 workers concurrently attempt to consume the same nonce.
        Invariant: Exactly 1 worker succeeds (returns consumed record), 9 fail with ValueError. Double consumptions = 0!
        """
        n_val = "n_race_1"
        tx_id = "tx_nc_1"
        man_id = "man_nc_1"

        await self.nonce_repo.create_nonce(n_val, tx_id, man_id)
        await self.session.commit()

        async def worker_consume(idx: int) -> bool:
            async with self.session_factory() as session_worker:
                repo_w = NonceRepository(session_worker)
                try:
                    await repo_w.consume_nonce(n_val, tx_id, man_id, ttl_seconds=300)
                    await session_worker.commit()
                    return True
                except ValueError:
                    await session_worker.rollback()
                    return False

        results = await asyncio.gather(*[worker_consume(i) for i in range(10)])
        successes = sum(1 for r in results if r is True)
        failures = sum(1 for r in results if r is False)

        self.assertEqual(successes, 1)
        self.assertEqual(failures, 9)

        # Final verification
        final_rec = await self.nonce_repo.get_nonce(n_val)
        self.assertIsNotNone(final_rec)
        self.assertEqual(final_rec.status, NonceState.CONSUMED.value)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
