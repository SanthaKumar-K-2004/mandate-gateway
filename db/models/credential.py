"""
S07.1 — API Credential Persistent ORM Model.

Stores API credential identity, salted secret hash, merchant binding, status,
and scopes for multi-tenant identity and authorization.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ApiCredentialModel(Base):
    """
    ORM model for durable API credential persistence.

    Primary Key: credential_id (e.g. 'cred_abc123')
    """

    __tablename__ = "api_credentials"

    credential_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        doc="Unique API credential identity.",
    )

    merchant_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Internal merchant ID owning this credential.",
    )

    credential_prefix: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Public non-secret prefix for credential lookup (e.g. 'rzp_live_abcd').",
    )

    credential_secret_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="Salted SHA-256 hash of the raw API secret.",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
        doc="Credential status: ACTIVE, REVOKED, EXPIRED.",
    )

    scopes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        doc="Space-delimited granted scopes (e.g. 'transaction:read transaction:write').",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        doc="UTC timestamp when the credential was created.",
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Optional UTC timestamp when the credential expires.",
    )

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Optional UTC timestamp when the credential was revoked.",
    )

    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Optional UTC timestamp when the credential was last authenticated.",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to a dictionary representation (excludes secret hash)."""
        return {
            "credential_id": self.credential_id,
            "merchant_id": self.merchant_id,
            "credential_prefix": self.credential_prefix,
            "status": self.status,
            "scopes": self.scopes.split() if self.scopes else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }
