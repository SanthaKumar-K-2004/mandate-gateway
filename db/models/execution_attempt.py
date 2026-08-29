"""
M07 — Execution Attempt Durable Ownership ORM Model.

Stores execution attempt ownership records to guarantee exactly-once external payment
effect dispatch across process crashes, retries, and concurrent workers.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ExecutionAttemptModel(Base):
    """
    ORM Model for tracking external payment provider execution attempts.

    Enforces that an execution ownership claim must be established before calling
    an external payment provider.
    """

    __tablename__ = "execution_attempts"

    attempt_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        doc="Unique attempt identity (UUIDv4 or exec:tx_id:attempt_num).",
    )

    transaction_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Linked internal transaction ID.",
    )

    merchant_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Merchant identity owning this execution.",
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Provider-level or execution-level idempotency key.",
    )

    payload_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 hex digest of trusted execution request payload.",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="CLAIMED",
        index=True,
        doc="Attempt lifecycle status: CLAIMED, DISPATCHED, SUCCESS, FAILED, UNKNOWN.",
    )

    provider_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="External provider order ID or payment ID if returned.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        doc="UTC timestamp when attempt ownership was claimed.",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="UTC timestamp when attempt outcome was finalized.",
    )

    __table_args__ = (
        Index("idx_exec_attempts_tx_status", "transaction_id", "status"),
        Index("idx_exec_attempts_merchant_idem", "merchant_id", "idempotency_key"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExecutionAttemptModel(attempt_id={self.attempt_id!r}, transaction_id={self.transaction_id!r}, "
            f"status={self.status!r}, provider_reference={self.provider_reference!r})>"
        )
