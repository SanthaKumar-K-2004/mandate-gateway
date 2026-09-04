"""
Section M15 — ForensicRepository for immutable forensic evidence storage & retrieval.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.forensic_event import ForensicEventModel
from db.repository.base import BaseRepository


class ForensicRepository(BaseRepository[ForensicEventModel]):
    """Repository for appending and querying immutable forensic events."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ForensicEventModel, session)

    async def record_event(self, event: ForensicEventModel) -> ForensicEventModel:
        """Appends a forensic event to the database."""
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_event_by_id(self, event_id: str) -> ForensicEventModel | None:
        """Finds a forensic event by ID."""
        stmt = select(ForensicEventModel).where(ForensicEventModel.event_id == event_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def query_events(
        self,
        category: str | None = None,
        severity: str | None = None,
        merchant_id: str | None = None,
        limit: int = 100,
    ) -> list[ForensicEventModel]:
        """Queries forensic events matching filters."""
        stmt = select(ForensicEventModel)
        if category:
            stmt = stmt.where(ForensicEventModel.category == category)
        if severity:
            stmt = stmt.where(ForensicEventModel.severity == severity)
        if merchant_id:
            stmt = stmt.where(ForensicEventModel.merchant_id == merchant_id)
        stmt = stmt.order_by(ForensicEventModel.created_at.desc()).limit(limit)
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

    async def list_events_by_correlation_id(self, correlation_id: str) -> list[ForensicEventModel]:
        """Lists forensic events for a correlation ID."""
        stmt = (
            select(ForensicEventModel)
            .where(ForensicEventModel.correlation_id == correlation_id)
            .order_by(ForensicEventModel.created_at.asc())
        )
        res = await self._session.execute(stmt)
        return list(res.scalars().all())
