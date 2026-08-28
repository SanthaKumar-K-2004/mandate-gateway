"""
S01.1 — Nonce Data Contract.

Single-use execution authorization nonce contract (Section 15, PROJECT_CONTEXT.md).

Data contracts only — consumption & freshness validation belong to S01.9 (nonce_engine.py).
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from apps.api.domain.types import NonceState


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


def generate_nonce() -> str:
    """Generate 32 hex character cryptographically random nonce."""
    return secrets.token_hex(16)


class NonceRecord(BaseModel):
    """
    Single-use nonce contract for an execution authorization.

    Data contract only.
    """

    model_config = {"frozen": True}

    nonce_id: str = Field(default_factory=_new_uuid)
    nonce_value: str = Field(
        ...,
        min_length=16,
        description="Cryptographically secure random nonce value (hex string).",
    )
    transaction_id: str = Field(..., min_length=1)
    mandate_id: str = Field(..., min_length=1)
    state: NonceState = Field(default=NonceState.ISSUED)

    issued_at: datetime = Field(default_factory=_utc_now)
    expires_at: datetime = Field(
        ...,
        description="UTC datetime after which this nonce is no longer valid.",
    )
    consumed_at: datetime | None = Field(
        default=None,
        description="Timestamp when the nonce was consumed. None if still ISSUED.",
    )

    def is_expired(self, at: datetime | None = None) -> bool:
        """Return True if the nonce has passed its expiry time."""
        check_time = at if at is not None else _utc_now()
        return check_time >= self.expires_at


class NonceAlreadyConsumedError(ValueError):
    """Raised when a previously consumed nonce is submitted again."""


class AuthorizationExpiredError(ValueError):
    """Raised when an execution authorization nonce has expired."""
