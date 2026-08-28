"""
Replay Fingerprint & Nonce ORM Models.
Section S05.2 — ORM Data Models & Alembic Schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base, utc_now


class ReplayRecordModel(Base):
    """Durable audit history of single-use proposal replay fingerprints."""

    __tablename__ = "replay_records"

    fingerprint: Mapped[str] = mapped_column(String(128), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)


class NonceRecordModel(Base):
    """Durable audit history of single-use cryptographic nonces."""

    __tablename__ = "nonce_records"

    nonce: Mapped[str] = mapped_column(String(128), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mandate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # ISSUED, CONSUMED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
