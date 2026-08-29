"""
S06.2 — Webhook Repository & Durable Provider Event Deduplication.

Domain persistence repository for provider webhook event registration,
primary-key deduplication, context correlation, and row locking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.webhook import WebhookEventModel
from db.repository.base import BaseRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class WebhookRepository(BaseRepository[WebhookEventModel]):
    """
    Repository for durable management and deduplication of provider webhook events.

    Security & Deduplication Invariants:
      1. Webhook event_id is globally unique (Primary Key).
      2. Duplicate event delivery attempts trigger IntegrityError and return (record, is_duplicate=True).
      3. Dialect-aware FOR UPDATE row locking prevents multi-worker race conditions on concurrent webhooks.
      4. Repository methods flush mutations without internal commits.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WebhookEventModel, session)

    async def register_event(
        self,
        event_id: str,
        event_type: str,
        transaction_id: str,
        merchant_id: str,
        payload_hash: str,
        status: str = "PROCESSED",
    ) -> tuple[WebhookEventModel, bool]:
        """
        Atomically register a new provider webhook event.

        Returns:
            (WebhookEventModel, is_duplicate: bool)
            If event_id already exists in DB, fetches existing record and returns (record, True).
        """
        if not event_id or not event_id.strip():
            raise ValueError("Webhook event_id cannot be empty.")
        if not transaction_id or not transaction_id.strip():
            raise ValueError("Transaction ID cannot be empty.")
        if not merchant_id or not merchant_id.strip():
            raise ValueError("Merchant ID cannot be empty.")

        clean_event = event_id.strip()
        clean_tx = transaction_id.strip()
        clean_mer = merchant_id.strip()

        # Check existing record first
        existing = await self.get_by_id(clean_event)
        if existing is not None:
            return existing, True

        record = WebhookEventModel(
            event_id=clean_event,
            event_type=event_type.strip(),
            transaction_id=clean_tx,
            merchant_id=clean_mer,
            payload_hash=payload_hash.strip(),
            status=status,
            processed_at=_utc_now(),
        )

        self._session.add(record)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            dup = await self.get_by_id(clean_event)
            if dup is not None:
                return dup, True
            raise

        return record, False

    async def get_event(self, event_id: str) -> WebhookEventModel | None:
        """Fetch a webhook event by ID."""
        if not event_id:
            return None
        return await self.get_by_id(event_id.strip())

    async def get_events_for_transaction(
        self, transaction_id: str
    ) -> Sequence[WebhookEventModel]:
        """Fetch all webhook events linked to a given transaction ID."""
        stmt = (
            select(WebhookEventModel)
            .where(WebhookEventModel.transaction_id == transaction_id.strip())
            .order_by(WebhookEventModel.processed_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def lock_event_for_update(self, event_id: str) -> WebhookEventModel | None:
        """Acquire SELECT ... FOR UPDATE lock on WebhookEventModel."""
        bind = getattr(self._session, "bind", None)
        dialect = getattr(bind, "dialect", None)
        dialect_name = getattr(dialect, "name", "") if dialect else ""

        stmt = select(WebhookEventModel).where(WebhookEventModel.event_id == event_id.strip())
        if dialect_name != "sqlite":
            stmt = stmt.with_for_update()

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
