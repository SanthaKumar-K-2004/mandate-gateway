"""
Forensic Event ORM Model.
Section M15 — Deep Production Observability & Forensic Traceability.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base, utc_now


class ForensicEventModel(Base):
    """Immutable forensic event record for security, abuse, reliability, and data integrity tracking."""

    __tablename__ = "forensic_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    actor_principal_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, index=True
    )
    merchant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    target_resource: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    hash_signature: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
