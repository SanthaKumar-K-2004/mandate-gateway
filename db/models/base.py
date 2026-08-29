"""
Mandate Gateway — SQLAlchemy 2.0 Declarative Base & Common Mixins.
Section S05.2 — ORM Data Models & Alembic Schema.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Authoritative base class for all SQLAlchemy 2.0 ORM models in Mandate Gateway."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM model attributes to dictionary representation."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        attrs = ", ".join(
            f"{c.name}={getattr(self, c.name)!r}"
            for c in self.__table__.columns
            if "password" not in c.name and "secret" not in c.name
        )
        return f"<{self.__class__.__name__}({attrs})>"


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)
