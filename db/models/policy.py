"""
Merchant Policy ORM Model.
Section S05.2 — ORM Data Models & Alembic Schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, utc_now

if TYPE_CHECKING:
    from db.models.merchant import MerchantModel


class MerchantPolicyModel(Base):
    """Durable representation of merchant policy rules and versioning."""

    __tablename__ = "merchant_policies"
    __table_args__ = (
        UniqueConstraint("merchant_id", "policy_version", name="uq_merchant_policy_version"),
        CheckConstraint("autonomous_limit_paise >= 0", name="chk_policy_autonomous_limit_non_negative"),
        CheckConstraint("step_up_threshold_paise >= 0", name="chk_policy_step_up_threshold_non_negative"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(64), ForeignKey("merchants.merchant_id", ondelete="CASCADE"), nullable=False, index=True)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    autonomous_limit_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    step_up_threshold_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    allowed_categories_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    allowed_operations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    blocked_operations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    merchant: Mapped["MerchantModel"] = relationship("MerchantModel", back_populates="policies")
