"""
M07 — Transactional Outbox ORM Model.

Stores domain event side-effects generated within the same database transaction
as state mutations, ensuring reliable eventual dispatch.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class OutboxEventModel(Base):
    """
    ORM Model for Transactional Outbox pattern.

    Primary Key: outbox_id (UUIDv4 string)
    """

    __tablename__ = "outbox_events"

    outbox_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        doc="Unique outbox record ID.",
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Domain event name (e.g. PAYMENT_COMMITTED, PAYMENT_ROLLED_BACK).",
    )

    aggregate_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Aggregate root type (e.g. TRANSACTION, MANDATE).",
    )

    aggregate_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Aggregate root identity (e.g. transaction_id).",
    )

    payload_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Canonical JSON payload of the event.",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
        index=True,
        doc="Outbox delivery status: PENDING, DISPATCHED, or FAILED.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        doc="UTC timestamp of event generation.",
    )

    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="UTC timestamp of successful event dispatch.",
    )

    def __repr__(self) -> str:
        return (
            f"<OutboxEventModel(outbox_id={self.outbox_id!r}, event_type={self.event_type!r}, "
            f"aggregate_id={self.aggregate_id!r}, status={self.status!r})>"
        )
