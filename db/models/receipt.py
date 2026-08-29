"""
Action Receipt ORM Model.
Section S05.2 — ORM Data Models & Alembic Schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, utc_now

if TYPE_CHECKING:
    from db.models.audit import AuditEventModel
    from db.models.transaction import TransactionModel


class ActionReceiptModel(Base):
    """Durable representation of Ed25519 signed action receipts."""

    __tablename__ = "action_receipts"

    receipt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("transactions.transaction_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    audit_event_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("audit_events.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    canonical_payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_hex: Mapped[str] = mapped_column(Text, nullable=False)
    public_key_hex: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    transaction: Mapped["TransactionModel"] = relationship(
        "TransactionModel", back_populates="receipts"
    )
    audit_event: Mapped["AuditEventModel"] = relationship(
        "AuditEventModel", back_populates="receipts"
    )
