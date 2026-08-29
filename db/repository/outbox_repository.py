"""
M07 — OutboxRepository & Transactional Outbox Persistence.

Domain repository for creating, retrieving, and dispatching outbox events
within database transaction boundaries.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.outbox import OutboxEventModel
from db.repository.base import BaseRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class OutboxRepository(BaseRepository[OutboxEventModel]):
    """
    Repository for managing transactional outbox records.

    Guarantees:
      - Outbox events are created within caller's active AsyncSession transaction.
      - Flush operations prepare records for commit without issuing internal commits.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OutboxEventModel, session)

    async def create_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        outbox_id: str | None = None,
    ) -> OutboxEventModel:
        """
        Record a new outbox event inside caller transaction.
        """
        evt_id = outbox_id or f"outbox_{uuid.uuid4().hex[:16]}"
        payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))

        record = OutboxEventModel(
            outbox_id=evt_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload_json=payload_str,
            status="PENDING",
            created_at=_utc_now(),
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_pending_events(self, limit: int = 100) -> Sequence[OutboxEventModel]:
        """Fetch oldest pending outbox events for dispatch worker."""
        stmt = (
            select(OutboxEventModel)
            .where(OutboxEventModel.status == "PENDING")
            .order_by(OutboxEventModel.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def mark_dispatched(self, outbox_id: str) -> OutboxEventModel:
        """Mark an outbox event as DISPATCHED."""
        record = await self.get_by_id(outbox_id)
        if record is None:
            raise ValueError(f"Outbox record '{outbox_id}' not found.")

        record.status = "DISPATCHED"
        record.dispatched_at = _utc_now()
        await self._session.flush()
        return record

    async def mark_failed(self, outbox_id: str) -> OutboxEventModel:
        """Mark an outbox event as FAILED."""
        record = await self.get_by_id(outbox_id)
        if record is None:
            raise ValueError(f"Outbox record '{outbox_id}' not found.")

        record.status = "FAILED"
        await self._session.flush()
        return record
