"""
S06.1 — Webhook Event Persistent ORM Model.

Stores incoming provider webhook event metadata for replay protection,
event deduplication, and context correlation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class WebhookEventModel(Base):
    """
    ORM model for durable provider webhook event deduplication & audit linking.

    Primary Key: event_id (provider unique event identity, e.g., 'event_12345')
    """

    __tablename__ = "webhook_events"

    event_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        doc="Provider unique event identity.",
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Provider event name (e.g. payment.authorized, payment.failed).",
    )

    transaction_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Internal transaction ID linked to this webhook.",
    )

    merchant_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Internal merchant ID linked to this webhook.",
    )

    payload_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 hex digest of raw webhook payload bytes.",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PROCESSED",
        doc="Event processing state: PROCESSED, DUPLICATE, or REJECTED.",
    )

    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        doc="UTC timestamp of event ingestion.",
    )

    def __repr__(self) -> str:
        return (
            f"<WebhookEventModel(event_id={self.event_id!r}, event_type={self.event_type!r}, "
            f"transaction_id={self.transaction_id!r}, status={self.status!r})>"
        )
