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

        from apps.api.app.metrics import metrics_registry

        metrics_registry.increment_counter(
            "outbox_events_created_total",
            labels={"event_type": event_type, "aggregate_type": aggregate_type},
        )
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

    async def get_pending_count(self) -> int:
        """Count total pending outbox events."""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(OutboxEventModel)
            .where(OutboxEventModel.status == "PENDING")
        )
        result = await self._session.execute(stmt)
        count = int(result.scalar_one_or_none() or 0)

        from apps.api.app.metrics import metrics_registry

        metrics_registry.set_gauge("outbox_events_pending", float(count))
        return count

    async def get_oldest_pending_age_seconds(self) -> float:
        """Calculate age of oldest pending event in seconds."""
        stmt = (
            select(OutboxEventModel)
            .where(OutboxEventModel.status == "PENDING")
            .order_by(OutboxEventModel.created_at.asc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        oldest = result.scalar_one_or_none()
        if oldest is None:
            age = 0.0
        else:
            created_at = oldest.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age = max(0.0, (_utc_now() - created_at).total_seconds())

        from apps.api.app.metrics import metrics_registry

        metrics_registry.set_gauge("outbox_oldest_event_age_seconds", age)
        return age

    async def mark_dispatched(self, outbox_id: str) -> OutboxEventModel:
        """Mark an outbox event as DISPATCHED."""
        record = await self.get_by_id(outbox_id)
        if record is None:
            raise ValueError(f"Outbox record '{outbox_id}' not found.")

        record.status = "DISPATCHED"
        record.dispatched_at = _utc_now()
        await self._session.flush()

        from apps.api.app.metrics import metrics_registry

        metrics_registry.increment_counter(
            "outbox_events_published_total",
            labels={"event_type": record.event_type, "aggregate_type": record.aggregate_type},
        )
        return record

    async def mark_failed(self, outbox_id: str) -> OutboxEventModel:
        """Mark an outbox event as FAILED."""
        record = await self.get_by_id(outbox_id)
        if record is None:
            raise ValueError(f"Outbox record '{outbox_id}' not found.")

        record.status = "FAILED"
        await self._session.flush()

        from apps.api.app.metrics import metrics_registry

        metrics_registry.increment_counter(
            "outbox_publish_failures_total",
            labels={"event_type": record.event_type, "aggregate_type": record.aggregate_type},
        )
        return record
