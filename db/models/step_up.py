"""
Step-Up Challenge ORM Model.
Section S05.2 — ORM Data Models & Alembic Schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, utc_now

if TYPE_CHECKING:
    from db.models.transaction import TransactionModel


class StepUpChallengeModel(Base):
    """Durable step-up human verification challenge storage."""

    __tablename__ = "step_up_challenges"

    challenge_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("transactions.transaction_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # PENDING, APPROVED, REJECTED, EXPIRED
    risk_classification: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approver_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    transaction: Mapped["TransactionModel"] = relationship(
        "TransactionModel", back_populates="step_up_challenges"
    )
