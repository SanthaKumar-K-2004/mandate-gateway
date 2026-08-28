"""
S01.1 — Audit Event Domain Model.

Every security-relevant state transition produces an audit event
(Section 19, PROJECT_CONTEXT.md).

Properties:
  - Append-only: events are never modified after creation.
  - Immutable: AuditEvent is frozen.
  - Hash-chained: each event records the hash of the previous event.
  - Deterministic: same event data always produces the same hash.

Hash chain:
    H0 = genesis (all-zeros SHA-256)
    H1 = SHA256(H0 + canonical(payload1))
    H2 = SHA256(H1 + canonical(payload2))
    ...

Audit event types (Section 19, PROJECT_CONTEXT.md):
    MANDATE_CREATED, MERCHANT_POLICY_CREATED, CART_PROPOSED,
    POLICY_EVALUATED, STEP_UP_REQUESTED, STEP_UP_APPROVED,
    RESERVATION_CREATED, TOOL_BLOCKED, EXECUTION_AUTHORIZED,
    PAYMENT_STARTED, PAYMENT_SUCCESS, PAYMENT_FAILED,
    RESERVATION_RELEASED, NONCE_REPLAY_BLOCKED, CART_TAMPER_BLOCKED
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from apps.api.domain.types import AuditEventType

# Sentinel "genesis" previous hash for the first event in a chain.
GENESIS_HASH: str = "0" * 64  # 64 hex zeros


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class AuditEvent(BaseModel):
    """
    Immutable, append-only audit event with cryptographic hash chain linkage.

    Never modify an AuditEvent after creation.
    Use AuditEvent.create() to generate a new event linked to the previous hash.
    """

    model_config = {"frozen": True}

    event_id: str = Field(default_factory=_new_uuid)
    event_type: AuditEventType
    timestamp: datetime = Field(default_factory=_utc_now)

    # Participants
    transaction_id: str | None = Field(default=None)
    mandate_id: str | None = Field(default=None)
    merchant_id: str | None = Field(default=None)
    buyer_id: str | None = Field(default=None)

    # Structured payload (sanitized — no secrets)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Event-specific structured data. "
            "Must NOT contain credentials, raw keys, or secret values."
        ),
    )

    # Hash chain
    previous_hash: str = Field(
        default=GENESIS_HASH,
        description=(
            "SHA-256 hex digest of the previous audit event. "
            "GENESIS_HASH (64 zeros) for the first event."
        ),
    )
    event_hash: str = Field(
        default="",
        description="SHA-256 hex digest of this event (computed on creation).",
    )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        event_type: AuditEventType,
        previous_hash: str = GENESIS_HASH,
        *,
        transaction_id: str | None = None,
        mandate_id: str | None = None,
        merchant_id: str | None = None,
        buyer_id: str | None = None,
        payload: dict[str, Any] | None = None,
        at: datetime | None = None,
    ) -> AuditEvent:
        """
        Create a new AuditEvent and compute its hash.

        Args:
            event_type: The type of security-relevant event.
            previous_hash: Hash of the immediately preceding event
                           (GENESIS_HASH for the first event in a ledger).
            **kwargs: Optional participant and payload fields.

        Returns:
            Fully populated, immutable AuditEvent with event_hash computed.
        """
        timestamp = at if at is not None else _utc_now()
        event_id = _new_uuid()
        safe_payload = payload or {}

        # Compute the canonical event hash
        event_hash = _compute_event_hash(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            previous_hash=previous_hash,
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            merchant_id=merchant_id,
            buyer_id=buyer_id,
            payload=safe_payload,
        )

        return cls(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            merchant_id=merchant_id,
            buyer_id=buyer_id,
            payload=safe_payload,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )

    def verify_hash(self) -> bool:
        """
        Recompute and verify the event_hash against current fields.

        Returns True if the event has not been tampered with.
        """
        expected = _compute_event_hash(
            event_id=self.event_id,
            event_type=self.event_type,
            timestamp=self.timestamp,
            previous_hash=self.previous_hash,
            transaction_id=self.transaction_id,
            mandate_id=self.mandate_id,
            merchant_id=self.merchant_id,
            buyer_id=self.buyer_id,
            payload=self.payload,
        )
        return self.event_hash == expected


# ---------------------------------------------------------------------------
# Hash computation (deterministic, pure)
# ---------------------------------------------------------------------------


def _compute_event_hash(
    *,
    event_id: str,
    event_type: AuditEventType,
    timestamp: datetime,
    previous_hash: str,
    transaction_id: str | None,
    mandate_id: str | None,
    merchant_id: str | None,
    buyer_id: str | None,
    payload: dict[str, Any],
) -> str:
    """
    Compute SHA-256 hash of a canonical audit event representation.

    The canonical form is a JSON object with sorted keys.
    Timestamps are serialized as ISO 8601 UTC strings.
    None values are serialized as null.
    """
    canonical: dict[str, Any] = {
        "buyer_id": buyer_id,
        "event_id": event_id,
        "event_type": event_type.value,
        "mandate_id": mandate_id,
        "merchant_id": merchant_id,
        "payload": payload,
        "previous_hash": previous_hash,
        "timestamp": timestamp.isoformat(),
        "transaction_id": transaction_id,
    }
    serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
