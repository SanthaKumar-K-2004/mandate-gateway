"""
Transaction Lifecycle ORM Model.
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
    from db.models.mandate import MandateModel
    from db.models.receipt import ActionReceiptModel
    from db.models.step_up import StepUpChallengeModel


class TransactionModel(Base):
    """Durable representation of transaction authorization & payment execution lifecycle."""

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount_paise >= 0", name="chk_transaction_amount_non_negative"),
    )

    transaction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    buyer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    merchant_id: Mapped[str] = mapped_column(String(64), ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    mandate_id: Mapped[str] = mapped_column(String(64), ForeignKey("mandates.mandate_id"), nullable=False, index=True)
    cart_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    region: Mapped[str] = mapped_column(String(32), default="IN", nullable=False)
    auth_decision: Mapped[str] = mapped_column(String(32), nullable=False)  # ALLOW, REQUIRE_STEP_UP, REJECT
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # INITIATED, AUTHORIZED, EXECUTED, FAILED, CANCELLED
    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    provider_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    mandate: Mapped["MandateModel"] = relationship("MandateModel", back_populates="transactions")
    reservations: Mapped[List["BudgetReservationModel"]] = relationship("BudgetReservationModel", back_populates="transaction")
    step_up_challenges: Mapped[List["StepUpChallengeModel"]] = relationship("StepUpChallengeModel", back_populates="transaction")
    receipts: Mapped[List["ActionReceiptModel"]] = relationship("ActionReceiptModel", back_populates="transaction")
