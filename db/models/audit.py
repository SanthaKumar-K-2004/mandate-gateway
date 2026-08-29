"""
Audit Event Ledger ORM Model.
Section S05.2 — ORM Data Models & Alembic Schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, utc_now

if TYPE_CHECKING:
    from db.models.receipt import ActionReceiptModel


class AuditEventModel(Base):
    """Durable append-only SHA-256 hash chained audit event record."""

    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sequence_number: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    transaction_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    mandate_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    merchant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    buyer_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    # Relationships
    receipts: Mapped[List["ActionReceiptModel"]] = relationship(
        "ActionReceiptModel", back_populates="audit_event"
    )
