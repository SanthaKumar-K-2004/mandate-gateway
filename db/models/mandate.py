"""
Buyer Mandate ORM Model.
Section S05.2 — ORM Data Models & Alembic Schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, utc_now

if TYPE_CHECKING:
    from db.models.budget import BudgetReservationModel
    from db.models.transaction import TransactionModel


class MandateModel(Base):
    """Durable representation of buyer pre-authorized mandates."""

    __tablename__ = "mandates"
    __table_args__ = (
        CheckConstraint("daily_budget_paise >= 0", name="chk_mandate_daily_budget_non_negative"),
    )

    mandate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    buyer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    merchant_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("merchants.merchant_id", ondelete="SET NULL"), nullable=True, index=True)
    category_scope: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    daily_budget_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cumulative_budget_paise: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    region: Mapped[str] = mapped_column(String(32), default="IN", nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # ACTIVE, REVOKED, EXPIRED
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    transactions: Mapped[List["TransactionModel"]] = relationship("TransactionModel", back_populates="mandate")
    reservations: Mapped[List["BudgetReservationModel"]] = relationship("BudgetReservationModel", back_populates="mandate")
