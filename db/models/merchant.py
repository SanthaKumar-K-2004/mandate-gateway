"""
Merchant ORM Model.
Section S05.2 — ORM Data Models & Alembic Schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, utc_now

if TYPE_CHECKING:
    from db.models.policy import MerchantPolicyModel
    from db.models.product import ProductModel


class MerchantModel(Base):
    """Durable representation of a merchant capable of AI commerce."""

    __tablename__ = "merchants"

    merchant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    razorpay_account_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    policies: Mapped[List["MerchantPolicyModel"]] = relationship("MerchantPolicyModel", back_populates="merchant", cascade="all, delete-orphan")
    products: Mapped[List["ProductModel"]] = relationship("ProductModel", back_populates="merchant", cascade="all, delete-orphan")
