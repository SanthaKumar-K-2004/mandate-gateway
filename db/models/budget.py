"""
Budget Reservation ORM Model.
Section S05.2 — ORM Data Models & Alembic Schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, utc_now

if TYPE_CHECKING:
    from db.models.mandate import MandateModel
    from db.models.transaction import TransactionModel


class BudgetReservationModel(Base):
    """Durable budget reservation storage for atomic spending isolation."""

    __tablename__ = "budget_reservations"
    __table_args__ = (
        UniqueConstraint("mandate_id", "transaction_id", name="uq_mandate_transaction_reservation"),
        CheckConstraint("requested_paise >= 0", name="chk_reservation_requested_non_negative"),
        CheckConstraint("reserved_paise >= 0", name="chk_reservation_reserved_non_negative"),
    )

    reservation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mandate_id: Mapped[str] = mapped_column(String(64), ForeignKey("mandates.mandate_id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(64), ForeignKey("transactions.transaction_id", ondelete="CASCADE"), nullable=False, index=True)
    requested_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reserved_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # RESERVED, COMMITTED, RELEASED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    mandate: Mapped["MandateModel"] = relationship("MandateModel", back_populates="reservations")
    transaction: Mapped["TransactionModel"] = relationship("TransactionModel", back_populates="reservations")
