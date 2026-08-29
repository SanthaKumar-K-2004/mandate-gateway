"""
S05.3.6.2 — ReplayRepository & Durable Replay Protection Persistence.

Domain persistence repository for single-use proposal replay fingerprints,
context binding, TTL expiry evaluation, and database concurrency protection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.replay import ReplayRecordModel
from db.repository.base import BaseRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ReplayRepository(BaseRepository[ReplayRecordModel]):
    """
    Repository for durable management of single-use proposal replay fingerprints.

    Core Security Invariant:
      A replay fingerprint that has already been consumed within its valid protection
      window must NOT be accepted again.

    Security & Persistence Rules:
      1. Replay records are immutable security evidence once created.
      2. Duplicate consumption of an active fingerprint is rejected.
      3. Context binding (transaction_id) is enforced; conflicting context reuse raises ValueError.
      4. TTL expiry semantics are evaluated using timezone-aware UTC timestamps.
      5. Primary key uniqueness constraints enforce multi-worker concurrency protection in PostgreSQL.
      6. Repository methods flush mutations to the underlying session without committing internally.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ReplayRecordModel, session)

    async def record_replay_fingerprint(
        self,
        fingerprint: str,
        transaction_id: str,
        created_at: datetime | None = None,
    ) -> ReplayRecordModel:
        """
        Record a new replay fingerprint evidence record.

        Flushes to session to trigger database primary key uniqueness check.
        """
        if not fingerprint or not fingerprint.strip():
            raise ValueError("Replay fingerprint cannot be empty.")
        if not transaction_id or not transaction_id.strip():
            raise ValueError("Transaction ID cannot be empty.")

        rec_time = created_at if created_at is not None else _utc_now()
        record = ReplayRecordModel(
            fingerprint=fingerprint.strip(),
            transaction_id=transaction_id.strip(),
            created_at=rec_time,
        )
        self._session.add(record)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ValueError(
                f"Replay fingerprint '{fingerprint}' already exists in persistence store."
            ) from exc
        return record

    async def get_replay_record(self, fingerprint: str) -> ReplayRecordModel | None:
        """Fetch a replay record by fingerprint primary key."""
        if not fingerprint:
            return None
        return await self.get_by_id(fingerprint.strip())

    async def get_replay_for_transaction(
        self, transaction_id: str
    ) -> Sequence[ReplayRecordModel]:
        """Fetch all replay records bound to a given transaction ID."""
        stmt = (
            select(ReplayRecordModel)
            .where(ReplayRecordModel.transaction_id == transaction_id)
            .order_by(ReplayRecordModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def lock_replay_for_update(
        self, fingerprint: str
    ) -> ReplayRecordModel | None:
        """Acquire SELECT ... FOR UPDATE row lock on ReplayRecordModel."""
        bind = getattr(self._session, "bind", None)
        dialect = getattr(bind, "dialect", None)
        dialect_name = getattr(dialect, "name", "") if dialect else ""

        stmt = select(ReplayRecordModel).where(
            ReplayRecordModel.fingerprint == fingerprint
        )
        if dialect_name != "sqlite":
            stmt = stmt.with_for_update()

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_fingerprint_replayed(
        self,
        fingerprint: str,
        ttl_seconds: int = 86400,
        at: datetime | None = None,
    ) -> bool:
        """
        Check if a replay fingerprint has been consumed and remains within active TTL window.

        Returns True if active replay attempt detected, False if absent or expired.
        """
        record = await self.get_replay_record(fingerprint)
        if record is None:
            return False

        check_time = at if at is not None else _utc_now()
        record_created = (
            record.created_at.replace(tzinfo=timezone.utc)
            if record.created_at.tzinfo is None
            else record.created_at
        )
        if ttl_seconds > 0:
            age_seconds = (check_time - record_created).total_seconds()
            if age_seconds >= ttl_seconds:
                return False  # Expired protection window

        return True

    async def check_and_record_replay(
        self,
        fingerprint: str,
        transaction_id: str,
        ttl_seconds: int = 86400,
        at: datetime | None = None,
    ) -> tuple[bool, ReplayRecordModel | None]:
        """
        Atomically check and record replay fingerprint.

        Returns:
            (is_replayed, record)
            - If active replay detected: returns (True, existing_record)
            - If new fingerprint: records and flushes, returns (False, new_record)

        Security Invariants:
            - Conflicting transaction context reuse raises ValueError.
            - Expired records allow new registration for clean replay window.
        """
        if not fingerprint or not fingerprint.strip():
            raise ValueError("Replay fingerprint cannot be empty.")
        if not transaction_id or not transaction_id.strip():
            raise ValueError("Transaction ID cannot be empty.")

        clean_fp = fingerprint.strip()
        clean_tx = transaction_id.strip()
        check_time = at if at is not None else _utc_now()

        existing = await self.lock_replay_for_update(clean_fp)
        if existing is not None:
            # Security Rule B: Conflicting context validation
            if existing.transaction_id != clean_tx:
                raise ValueError(
                    f"Conflicting context reuse detected for fingerprint '{clean_fp[:12]}...': "
                    f"original transaction '{existing.transaction_id}', attempted transaction '{clean_tx}'."
                )

            # Check TTL expiry
            if ttl_seconds > 0:
                age_seconds = (check_time - existing.created_at).total_seconds()
                if age_seconds < ttl_seconds:
                    return True, existing
            else:
                return True, existing

        # Record new valid replay fingerprint
        record = await self.record_replay_fingerprint(
            fingerprint=clean_fp,
            transaction_id=clean_tx,
            created_at=check_time,
        )
        return False, record
