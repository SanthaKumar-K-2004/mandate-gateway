"""
S05.3.7 — AuditRepository & Hash-Chained Audit Ledger Persistence.

Domain persistence repository for append-only, SHA-256 hash-chained audit events,
sequence number monotonicity, and cryptographic chain verification.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Sequence
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.domain.audit import GENESIS_HASH, _compute_event_hash
from apps.api.domain.types import AuditEventType
from db.models.audit import AuditEventModel
from db.repository.base import BaseRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class AuditRepository(BaseRepository[AuditEventModel]):
    """
    Repository for durable, append-only cryptographic audit event ledger.

    Core Security Invariant:
      Audit events are immutable security evidence. They can only be appended,
      never updated, mutated, or deleted.

    Hash-Chain Invariant:
      Event 1: previous_hash = GENESIS_HASH ("0" * 64)
      Event N: previous_hash = Event N-1.event_hash
      sequence_number: strictly monotonic (1, 2, 3, ...)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AuditEventModel, session)

    async def get_latest_event(self, lock: bool = True) -> AuditEventModel | None:
        """
        Retrieve the latest audit event in the chain by sequence_number.

        When lock=True, applies SELECT ... FOR UPDATE (dialect-aware) inside caller transaction
        to serialize concurrent audit appends across API nodes.
        """
        bind = getattr(self._session, "bind", None)
        dialect = getattr(bind, "dialect", None)
        dialect_name = getattr(dialect, "name", "") if dialect else ""

        stmt = select(AuditEventModel).order_by(AuditEventModel.sequence_number.desc()).limit(1)
        if lock and dialect_name != "sqlite":
            stmt = stmt.with_for_update()

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def append_event(
        self,
        event_type: str | AuditEventType,
        *,
        transaction_id: str | None = None,
        mandate_id: str | None = None,
        merchant_id: str | None = None,
        buyer_id: str | None = None,
        payload: dict[str, Any] | None = None,
        at: datetime | None = None,
        event_id: str | None = None,
    ) -> AuditEventModel:
        """
        Append a new AuditEventModel to the hash-chained ledger inside caller transaction.

        Atomically derives next sequence number and previous_hash from the latest event.
        Flushes to session without committing.
        """
        event_type_enum = (
            event_type if isinstance(event_type, AuditEventType) else AuditEventType(str(event_type))
        )
        event_type_str = event_type_enum.value

        event_time = at if at is not None else _utc_now()
        safe_payload = payload or {}

        # 1. Lock and fetch latest audit event in chain
        latest = await self.get_latest_event(lock=True)

        if latest is None:
            next_seq = 1
            prev_hash = GENESIS_HASH
        else:
            next_seq = latest.sequence_number + 1
            prev_hash = latest.event_hash

        import uuid

        evt_id = event_id or str(uuid.uuid4())

        # 2. Compute canonical event_hash using domain logic
        computed_hash = _compute_event_hash(
            event_id=evt_id,
            event_type=event_type_enum,
            timestamp=event_time,
            previous_hash=prev_hash,
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            merchant_id=merchant_id,
            buyer_id=buyer_id,
            payload=safe_payload,
        )

        payload_json_str = json.dumps(safe_payload, sort_keys=True, separators=(",", ":"))

        # 3. Create ORM model
        audit_event = AuditEventModel(
            event_id=evt_id,
            sequence_number=next_seq,
            event_type=event_type_str,
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            merchant_id=merchant_id,
            buyer_id=buyer_id,
            payload_json=payload_json_str,
            previous_hash=prev_hash,
            event_hash=computed_hash,
            timestamp=event_time,
        )

        self._session.add(audit_event)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ValueError(
                f"Failed to append audit event {evt_id} at sequence {next_seq}: integrity constraint violated."
            ) from exc

        return audit_event

    async def get_event(self, event_id: str) -> AuditEventModel | None:
        """Fetch audit event by primary key event_id."""
        if not event_id:
            return None
        return await self.get_by_id(event_id.strip())

    async def get_event_by_sequence(self, sequence_number: int) -> AuditEventModel | None:
        """Fetch audit event by unique sequence_number."""
        stmt = select(AuditEventModel).where(AuditEventModel.sequence_number == sequence_number)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_events_for_transaction(self, transaction_id: str) -> Sequence[AuditEventModel]:
        """Fetch all audit events for a transaction, ordered by sequence_number."""
        stmt = (
            select(AuditEventModel)
            .where(AuditEventModel.transaction_id == transaction_id)
            .order_by(AuditEventModel.sequence_number.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_all_events(self) -> Sequence[AuditEventModel]:
        """Fetch all audit events in the ledger, ordered by sequence_number ASC."""
        stmt = select(AuditEventModel).order_by(AuditEventModel.sequence_number.asc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def verify_chain(self) -> tuple[bool, str | None]:
        """
        Verify complete cryptographic hash-chain integrity from sequence 1 to head.

        Checks:
          1. Monotonic sequence numbers (1, 2, 3, ...) without gaps or reordering.
          2. Previous hash linkage (sequence 1 previous_hash == GENESIS_HASH, sequence N == N-1 event_hash).
          3. Exact canonical event_hash recomputation.
        """
        events = await self.get_all_events()
        if not events:
            return True, None

        expected_seq = 1
        expected_prev_hash = GENESIS_HASH

        for idx, event in enumerate(events):
            # Sequence check
            if event.sequence_number != expected_seq:
                return (
                    False,
                    f"Audit chain sequence broken at index {idx}: expected sequence {expected_seq}, got {event.sequence_number}.",
                )

            # Previous hash check
            if event.previous_hash != expected_prev_hash:
                return (
                    False,
                    f"Audit chain link broken at sequence {event.sequence_number}: "
                    f"previous_hash '{event.previous_hash}' != expected '{expected_prev_hash}'.",
                )

            # Hash calculation check
            try:
                payload_dict = json.loads(event.payload_json) if event.payload_json else {}
            except Exception as exc:
                return False, f"Invalid payload_json at sequence {event.sequence_number}: {exc}"

            try:
                event_type_enum = AuditEventType(event.event_type)
            except Exception:
                return False, f"Invalid event_type '{event.event_type}' at sequence {event.sequence_number}."

            recomputed_hash = _compute_event_hash(
                event_id=event.event_id,
                event_type=event_type_enum,
                timestamp=event.timestamp,
                previous_hash=event.previous_hash,
                transaction_id=event.transaction_id,
                mandate_id=event.mandate_id,
                merchant_id=event.merchant_id,
                buyer_id=event.buyer_id,
                payload=payload_dict,
            )

            if event.event_hash != recomputed_hash:
                return (
                    False,
                    f"Audit event_hash tampered at sequence {event.sequence_number}: "
                    f"stored '{event.event_hash}' != recomputed '{recomputed_hash}'.",
                )

            expected_seq += 1
            expected_prev_hash = event.event_hash

        return True, None
