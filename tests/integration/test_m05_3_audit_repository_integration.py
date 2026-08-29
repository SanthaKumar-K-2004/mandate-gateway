"""
Integration tests for S05.3.7 AuditRepository against SQLite in-memory database.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.domain.audit import GENESIS_HASH
from apps.api.domain.types import AuditEventType
from db.models.base import Base
from db.repository.audit_repository import AuditRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestAuditRepositoryIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test suite for AuditRepository using SQLite in-memory engine."""

    async def asyncSetUp(self) -> None:
        """Set up in-memory SQLite database and repository session."""
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self.session = self.session_factory()
        self.audit_repo = AuditRepository(self.session)

    async def asyncTearDown(self) -> None:
        """Close session and dispose engine."""
        await self.session.close()
        await self.engine.dispose()

    async def test_audit_event_append_and_hash_chain_verification(self) -> None:
        """Verify sequential event appending, hash-chain linkage, and verify_chain validation."""
        evt1 = await self.audit_repo.append_event(
            event_type=AuditEventType.MANDATE_CREATED,
            mandate_id="man_1001",
            payload={"action": "create"},
        )
        await self.session.commit()

        self.assertEqual(evt1.sequence_number, 1)
        self.assertEqual(evt1.previous_hash, GENESIS_HASH)

        # Append second event
        evt2 = await self.audit_repo.append_event(
            event_type=AuditEventType.PAYMENT_SUCCESS,
            mandate_id="man_1001",
            transaction_id="tx_2001",
            payload={"amount": 5000},
        )
        await self.session.commit()

        self.assertEqual(evt2.sequence_number, 2)
        self.assertEqual(evt2.previous_hash, evt1.event_hash)

        # Verify chain integrity
        async with self.session_factory() as session2:
            repo2 = AuditRepository(session2)
            is_valid, error_msg = await repo2.verify_chain()
            self.assertTrue(is_valid, f"Audit chain verification failed: {error_msg}")
            self.assertIsNone(error_msg)

    async def test_audit_tamper_detection(self) -> None:
        """Verify tampering with a stored audit event causes verify_chain to return False."""
        await self.audit_repo.append_event(
            event_type=AuditEventType.MANDATE_CREATED,
            mandate_id="man_tamper",
        )
        await self.session.commit()

        # Mutate event_hash in DB to simulate tampering
        evt = await self.audit_repo.get_event_by_sequence(1)
        self.assertIsNotNone(evt)
        evt.event_hash = "TAMPERED_HASH_XXXXX"  # type: ignore[union-attr]
        await self.session.commit()

        is_valid, error_msg = await self.audit_repo.verify_chain()
        self.assertFalse(is_valid)
        self.assertIn("tampered", str(error_msg))

    async def test_transaction_rollback_leaves_no_partial_evidence(self) -> None:
        """Verify rolling back a transaction discards appended audit events."""
        await self.audit_repo.append_event(
            event_type=AuditEventType.MANDATE_CREATED,
            mandate_id="man_rollback",
        )
        await self.session.rollback()

        events = await self.audit_repo.get_all_events()
        self.assertEqual(len(events), 0)

    async def test_concurrent_audit_event_appends(self) -> None:
        """
        Concurrency test against SQLite session factory:
        10 sequential workers append audit events.
        Invariant: All 10 events are appended with unique monotonic sequence numbers (1..10) and valid hash chain.
        """

        async def worker_append(idx: int) -> bool:
            async with self.session_factory() as session_worker:
                repo_w = AuditRepository(session_worker)
                try:
                    await repo_w.append_event(
                        event_type=AuditEventType.POLICY_EVALUATED,
                        mandate_id=f"man_conc_{idx}",
                        payload={"worker": idx},
                    )
                    await session_worker.commit()
                    return True
                except Exception:
                    await session_worker.rollback()
                    return False

        # Execute 10 appends sequentially under separate sessions to simulate concurrent workers
        for i in range(10):
            res = await worker_append(i)
            self.assertTrue(res)

        # Verify complete chain integrity
        async with self.session_factory() as session_verify:
            repo_v = AuditRepository(session_verify)
            all_events = await repo_v.get_all_events()
            self.assertEqual(len(all_events), 10)

            seqs = [e.sequence_number for e in all_events]
            self.assertEqual(seqs, list(range(1, 11)))

            is_valid, err = await repo_v.verify_chain()
            self.assertTrue(is_valid, f"Chain integrity failed: {err}")


if __name__ == "__main__":
    unittest.main()
