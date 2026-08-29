"""
S05.3.6.3 — NonceRepository & Durable Single-Use Cryptographic Nonce Persistence.

Domain persistence repository for cryptographic single-use nonces, context binding,
TTL expiry evaluation, state transition enforcement, and database row locking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.domain.types import NonceState
from db.models.replay import NonceRecordModel
from db.repository.base import BaseRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class NonceRepository(BaseRepository[NonceRecordModel]):
    """
    Repository for durable management of single-use cryptographic nonces.

    Core Security Invariant:
      A valid nonce may be consumed EXACTLY ONCE within its valid lifetime.

    Security & Persistence Rules:
      1. Nonces are bound to mandate_id AND transaction_id. Mismatched context fails closed.
      2. Status transitions strictly ISSUED -> CONSUMED. Re-consuming raises ValueError.
      3. Expiry is evaluated using UTC timestamps. Expired nonces cannot be consumed.
      4. Database row locking (SELECT ... FOR UPDATE) and Primary Key constraints enforce
         multi-worker concurrency protection across API nodes.
      5. Repository methods flush mutations to the underlying session without committing internally.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(NonceRecordModel, session)

    async def create_nonce(
        self,
        nonce: str,
        transaction_id: str,
        mandate_id: str,
        status: str | NonceState = NonceState.ISSUED,
        created_at: datetime | None = None,
    ) -> NonceRecordModel:
        """
        Create and persist a new cryptographic nonce record in ISSUED state.

        Flushes to session to trigger database primary key uniqueness check.
        """
        if not nonce or not nonce.strip():
            raise ValueError("Nonce value cannot be empty.")
        if not transaction_id or not transaction_id.strip():
            raise ValueError("Transaction ID cannot be empty.")
        if not mandate_id or not mandate_id.strip():
            raise ValueError("Mandate ID cannot be empty.")

        status_str = status.value if isinstance(status, NonceState) else str(status)
        rec_time = created_at if created_at is not None else _utc_now()

        record = NonceRecordModel(
            nonce=nonce.strip(),
            transaction_id=transaction_id.strip(),
            mandate_id=mandate_id.strip(),
            status=status_str,
            created_at=rec_time,
            consumed_at=None,
        )
        self._session.add(record)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ValueError(
                f"Nonce '{nonce}' already exists in persistence store."
            ) from exc
        return record

    async def get_nonce(self, nonce: str) -> NonceRecordModel | None:
        """Fetch a nonce record by nonce primary key."""
        if not nonce:
            return None
        return await self.get_by_id(nonce.strip())

    async def get_nonces_for_transaction(
        self, transaction_id: str
    ) -> Sequence[NonceRecordModel]:
        """Fetch all nonces bound to a given transaction ID."""
        stmt = (
            select(NonceRecordModel)
            .where(NonceRecordModel.transaction_id == transaction_id)
            .order_by(NonceRecordModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_nonces_for_mandate(
        self, mandate_id: str
    ) -> Sequence[NonceRecordModel]:
        """Fetch all nonces bound to a given mandate ID."""
        stmt = (
            select(NonceRecordModel)
            .where(NonceRecordModel.mandate_id == mandate_id)
            .order_by(NonceRecordModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def lock_nonce_for_update(
        self, nonce: str
    ) -> NonceRecordModel | None:
        """Acquire SELECT ... FOR UPDATE row lock on NonceRecordModel."""
        bind = getattr(self._session, "bind", None)
        dialect = getattr(bind, "dialect", None)
        dialect_name = getattr(dialect, "name", "") if dialect else ""

        stmt = select(NonceRecordModel).where(NonceRecordModel.nonce == nonce)
        if dialect_name != "sqlite":
            stmt = stmt.with_for_update()

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def consume_nonce(
        self,
        nonce: str,
        transaction_id: str,
        mandate_id: str,
        ttl_seconds: int = 300,
        at: datetime | None = None,
    ) -> NonceRecordModel:
        """
        Atomically consume a valid cryptographic nonce.

        Steps:
          1. Locks row for update inside caller transaction.
          2. Validates existence, context binding (transaction_id and mandate_id).
          3. Validates status: if CONSUMED, raises ValueError (single-use guarantee).
          4. Validates TTL expiry: if expired, raises ValueError.
          5. Mutates status to CONSUMED and records consumed_at timestamp.
          6. Flushes session without committing.
        """
        if not nonce or not nonce.strip():
            raise ValueError("Nonce value cannot be empty.")

        clean_nonce = nonce.strip()
        clean_tx = transaction_id.strip()
        clean_man = mandate_id.strip()
        eval_time = at if at is not None else _utc_now()

        record = await self.lock_nonce_for_update(clean_nonce)
        if record is None:
            raise ValueError(f"Nonce '{clean_nonce}' not found in persistence store.")

        # 1. Context binding validation
        if record.transaction_id != clean_tx or record.mandate_id != clean_man:
            raise ValueError(
                f"Nonce context mismatch for '{clean_nonce[:8]}...': "
                f"bound to tx='{record.transaction_id}', mandate='{record.mandate_id}'; "
                f"submitted for tx='{clean_tx}', mandate='{clean_man}'."
            )

        # 2. State transition validation (single-use guarantee)
        if record.status == NonceState.CONSUMED.value:
            raise ValueError(
                f"Nonce '{clean_nonce}' has already been consumed at {record.consumed_at}."
            )

        # 3. Expiration validation
        if ttl_seconds > 0:
            age_seconds = (eval_time - record.created_at).total_seconds()
            if age_seconds >= ttl_seconds:
                raise ValueError(
                    f"Nonce '{clean_nonce}' expired: created at {record.created_at}, "
                    f"evaluated at {eval_time} (age {age_seconds:.1f}s >= TTL {ttl_seconds}s)."
                )

        # Atomically consume
        record.status = NonceState.CONSUMED.value
        record.consumed_at = eval_time
        await self._session.flush()
        return record
