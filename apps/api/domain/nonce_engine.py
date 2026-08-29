"""
S01.9 — Nonce & Authorization Freshness Engine.

Enterprise-grade, thread-safe nonce consumption and request freshness engine (Section 15, PROJECT_CONTEXT.md).

Lifecycle:
    ISSUED → CONSUMED

Security Boundaries:
    1. Single-Use Guarantee: Exactly one successful consumption per nonce value.
    2. Identity Binding: Nonces are bound to mandate_id and transaction_id.
    3. Expiration: Nonces past expires_at raise AuthorizationExpiredError / REJECT.
    4. Time Safety: Timezone-aware UTC timestamps used for all issuance and expiration checks.
    5. Atomic Consumption: Linearizable thread synchronization under RLock prevents concurrent double-consumption.
    6. Non-Destructive Failure: Invalid validation attempts do NOT mark ISSUED nonces as CONSUMED.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from typing import TYPE_CHECKING

from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.nonce import (
    AuthorizationExpiredError,
    NonceAlreadyConsumedError,
    NonceRecord,
    generate_nonce,
)
from apps.api.domain.types import NonceState, PolicyDecision, RejectionReason

if TYPE_CHECKING:
    from db.unit_of_work import AsyncUnitOfWork


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def assert_nonce_consumable(record: NonceRecord, at: datetime | None = None) -> None:
    """
    Raise the appropriate error if the nonce cannot be consumed.

    Raises:
        NonceAlreadyConsumedError: if nonce is already CONSUMED.
        AuthorizationExpiredError: if nonce has expired.
    """
    now = at if at is not None else _utc_now()
    if record.state is NonceState.CONSUMED:
        raise NonceAlreadyConsumedError(
            f"Nonce {record.nonce_value!r} has already been consumed "
            f"(consumed_at={record.consumed_at})."
        )
    if now >= record.expires_at:
        raise AuthorizationExpiredError(
            f"Nonce {record.nonce_value!r} expired at {record.expires_at.isoformat()}."
        )


def consume_nonce(record: NonceRecord, at: datetime | None = None) -> NonceRecord:
    """
    Mark the nonce as consumed (returns new immutable instance).

    Raises NonceAlreadyConsumedError or AuthorizationExpiredError if
    the nonce cannot be consumed.
    """
    assert_nonce_consumable(record, at)
    consumed_time = at if at is not None else _utc_now()
    return record.model_copy(
        update={
            "state": NonceState.CONSUMED,
            "consumed_at": consumed_time,
        }
    )


@dataclass(frozen=True, slots=True)
class NonceEvaluationResult:
    """Outcome of a nonce validation and consumption evaluation."""

    valid: bool
    decision: PolicyDecision
    nonce_value: str
    mandate_id: str
    transaction_id: str
    record: NonceRecord | None = None
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    evaluated_at: datetime = field(default_factory=_utc_now)

    @property
    def is_allowed(self) -> bool:
        return self.valid and self.decision == PolicyDecision.ALLOW

    def to_security_control_outcome(self) -> SecurityControlOutcome:
        """Convert result into a standardized S01.5 SecurityControlOutcome."""
        return SecurityControlOutcome(
            control_name="NONCE_VALIDATION",
            passed=self.valid,
            decision=self.decision,
            rejection_reason=self.rejection_reason,
            detail=self.rejection_detail,
        )


class NonceEngine:
    """
    Thread-safe, deterministic Nonce & Authorization Freshness Engine.

    Manages issuance, binding verification, expiration, and atomic single-use consumption.
    """

    def __init__(self) -> None:
        self._records: dict[str, NonceRecord] = {}
        self._lock = threading.RLock()

    def issue_nonce(
        self,
        mandate_id: str,
        transaction_id: str,
        ttl_seconds: int = 300,
        at: datetime | None = None,
    ) -> NonceRecord:
        """Issue a new cryptographically random authorization nonce bound to mandate and transaction."""
        if not mandate_id or not mandate_id.strip():
            raise ValueError("mandate_id cannot be empty")
        if not transaction_id or not transaction_id.strip():
            raise ValueError("transaction_id cannot be empty")

        issued_time = at if at is not None else _utc_now()
        expires_time = datetime.fromtimestamp(
            issued_time.timestamp() + ttl_seconds, tz=timezone.utc
        )
        value = generate_nonce()

        record = NonceRecord(
            nonce_value=value,
            mandate_id=mandate_id.strip(),
            transaction_id=transaction_id.strip(),
            state=NonceState.ISSUED,
            issued_at=issued_time,
            expires_at=expires_time,
            consumed_at=None,
        )

        with self._lock:
            self._records[value] = record
            return record

    def validate_and_consume(
        self,
        nonce_value: str,
        mandate_id: str,
        transaction_id: str,
        at: datetime | None = None,
    ) -> NonceEvaluationResult:
        """
        Atomically validate nonce format, binding, issuance, expiration, and state.

        If valid, atomically transition state to CONSUMED under RLock.
        Failed validation attempts do NOT consume or mutate ISSUED nonces.
        """
        eval_time = at if at is not None else _utc_now()
        clean_nonce = nonce_value.strip() if nonce_value else ""

        if not clean_nonce:
            return NonceEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                nonce_value=nonce_value,
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                rejection_reason=RejectionReason.NONCE_INVALID,
                rejection_detail="Nonce validation failed: Nonce value cannot be empty.",
                evaluated_at=eval_time,
            )

        with self._lock:
            record = self._records.get(clean_nonce)
            if record is None:
                return NonceEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    nonce_value=clean_nonce,
                    mandate_id=mandate_id,
                    transaction_id=transaction_id,
                    rejection_reason=RejectionReason.NONCE_INVALID,
                    rejection_detail=f"Nonce validation failed: Nonce {clean_nonce!r} not found in store.",
                    evaluated_at=eval_time,
                )

            # Validate identity binding
            if (
                record.mandate_id != mandate_id.strip()
                or record.transaction_id != transaction_id.strip()
            ):
                return NonceEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    nonce_value=clean_nonce,
                    mandate_id=mandate_id,
                    transaction_id=transaction_id,
                    record=record,
                    rejection_reason=RejectionReason.NONCE_INVALID,
                    rejection_detail=(
                        f"Nonce binding mismatch: Nonce {clean_nonce[:8]}... is bound to "
                        f"mandate={record.mandate_id!r}, tx={record.transaction_id!r}, but submitted for "
                        f"mandate={mandate_id!r}, tx={transaction_id!r}."
                    ),
                    evaluated_at=eval_time,
                )

            # Validate state
            if record.state is NonceState.CONSUMED:
                return NonceEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    nonce_value=clean_nonce,
                    mandate_id=mandate_id,
                    transaction_id=transaction_id,
                    record=record,
                    rejection_reason=RejectionReason.NONCE_ALREADY_CONSUMED,
                    rejection_detail=f"Nonce {clean_nonce!r} has already been consumed at {record.consumed_at}.",
                    evaluated_at=eval_time,
                )

            # Validate issuance timestamp
            if eval_time < record.issued_at:
                return NonceEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    nonce_value=clean_nonce,
                    mandate_id=mandate_id,
                    transaction_id=transaction_id,
                    record=record,
                    rejection_reason=RejectionReason.INVALID_TRANSACTION_STATE,
                    rejection_detail=f"Nonce {clean_nonce!r} issued in future ({record.issued_at.isoformat()}).",
                    evaluated_at=eval_time,
                )

            # Validate expiration timestamp
            if eval_time >= record.expires_at:
                return NonceEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    nonce_value=clean_nonce,
                    mandate_id=mandate_id,
                    transaction_id=transaction_id,
                    record=record,
                    rejection_reason=RejectionReason.AUTHORIZATION_EXPIRED,
                    rejection_detail=f"Nonce {clean_nonce!r} expired at {record.expires_at.isoformat()}.",
                    evaluated_at=eval_time,
                )

            # Atomically consume valid nonce
            consumed_record = record.model_copy(
                update={
                    "state": NonceState.CONSUMED,
                    "consumed_at": eval_time,
                }
            )
            self._records[clean_nonce] = consumed_record

            return NonceEvaluationResult(
                valid=True,
                decision=PolicyDecision.ALLOW,
                nonce_value=clean_nonce,
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                record=consumed_record,
                rejection_reason=None,
                rejection_detail=None,
                evaluated_at=eval_time,
            )

    def get_nonce(self, nonce_value: str) -> NonceRecord | None:
        """Read-only lookup of a nonce record."""
        clean = nonce_value.strip() if nonce_value else ""
        with self._lock:
            return self._records.get(clean)

    def record_count(self) -> int:
        """Return total number of active/recorded nonces."""
        with self._lock:
            return len(self._records)

    # -----------------------------------------------------------------------
    # Async Persistent Methods (S05.4 Domain Engine Persistence Integration)
    # -----------------------------------------------------------------------

    async def async_issue_nonce(
        self,
        uow: AsyncUnitOfWork,
        mandate_id: str,
        transaction_id: str,
        ttl_seconds: int = 300,
        at: datetime | None = None,
    ) -> NonceRecord:
        """Issue a new cryptographically random nonce and persist to database via uow.nonces."""
        if not mandate_id or not mandate_id.strip():
            raise ValueError("mandate_id cannot be empty")
        if not transaction_id or not transaction_id.strip():
            raise ValueError("transaction_id cannot be empty")

        issued_time = at if at is not None else _utc_now()
        expires_time = datetime.fromtimestamp(
            issued_time.timestamp() + ttl_seconds, tz=timezone.utc
        )
        value = generate_nonce()

        model = await uow.nonces.create_nonce(
            nonce=value,
            transaction_id=transaction_id.strip(),
            mandate_id=mandate_id.strip(),
            status=NonceState.ISSUED,
            created_at=issued_time,
        )

        record = NonceRecord(
            nonce_value=model.nonce,
            mandate_id=model.mandate_id,
            transaction_id=model.transaction_id,
            state=NonceState.ISSUED,
            issued_at=model.created_at,
            expires_at=expires_time,
            consumed_at=None,
        )

        with self._lock:
            self._records[value] = record
        return record

    async def async_validate_and_consume(
        self,
        uow: AsyncUnitOfWork,
        nonce_value: str,
        mandate_id: str,
        transaction_id: str,
        at: datetime | None = None,
        ttl_seconds: int = 300,
    ) -> NonceEvaluationResult:
        """
        Atomically validate nonce in database under row lock (FOR UPDATE).
        If valid, transition state to CONSUMED in database via uow.nonces.
        """
        eval_time = at if at is not None else _utc_now()
        clean_nonce = nonce_value.strip() if nonce_value else ""

        if not clean_nonce:
            return NonceEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                nonce_value=nonce_value,
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                rejection_reason=RejectionReason.NONCE_INVALID,
                rejection_detail="Nonce validation failed: Nonce value cannot be empty.",
                evaluated_at=eval_time,
            )

        model = await uow.nonces.lock_nonce_for_update(clean_nonce)
        if model is None:
            return NonceEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                nonce_value=clean_nonce,
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                rejection_reason=RejectionReason.NONCE_INVALID,
                rejection_detail=f"Nonce validation failed: Nonce {clean_nonce!r} not found in database.",
                evaluated_at=eval_time,
            )

        created_at_utc = (
            model.created_at.replace(tzinfo=timezone.utc)
            if model.created_at.tzinfo is None
            else model.created_at
        )
        expires_time = datetime.fromtimestamp(
            created_at_utc.timestamp() + ttl_seconds, tz=timezone.utc
        )
        domain_record = NonceRecord(
            nonce_value=model.nonce,
            mandate_id=model.mandate_id,
            transaction_id=model.transaction_id,
            state=NonceState(model.status),
            issued_at=model.created_at,
            expires_at=expires_time,
            consumed_at=model.consumed_at,
        )

        if model.mandate_id != mandate_id.strip() or model.transaction_id != transaction_id.strip():
            return NonceEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                nonce_value=clean_nonce,
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                record=domain_record,
                rejection_reason=RejectionReason.NONCE_INVALID,
                rejection_detail=(
                    f"Nonce binding mismatch: Nonce {clean_nonce[:8]}... is bound to "
                    f"mandate={model.mandate_id!r}, tx={model.transaction_id!r}, but submitted for "
                    f"mandate={mandate_id!r}, tx={transaction_id!r}."
                ),
                evaluated_at=eval_time,
            )

        if model.status == NonceState.CONSUMED.value:
            return NonceEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                nonce_value=clean_nonce,
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                record=domain_record,
                rejection_reason=RejectionReason.NONCE_ALREADY_CONSUMED,
                rejection_detail=f"Nonce {clean_nonce!r} has already been consumed at {model.consumed_at}.",
                evaluated_at=eval_time,
            )

        if eval_time >= expires_time:
            return NonceEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                nonce_value=clean_nonce,
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                record=domain_record,
                rejection_reason=RejectionReason.AUTHORIZATION_EXPIRED,
                rejection_detail=f"Nonce {clean_nonce!r} expired at {expires_time.isoformat()}.",
                evaluated_at=eval_time,
            )

        consumed_model = await uow.nonces.consume_nonce(
            nonce=clean_nonce,
            transaction_id=transaction_id.strip(),
            mandate_id=mandate_id.strip(),
            at=eval_time,
        )

        consumed_record = domain_record.model_copy(
            update={
                "state": NonceState.CONSUMED,
                "consumed_at": consumed_model.consumed_at or eval_time,
            }
        )

        with self._lock:
            self._records[clean_nonce] = consumed_record

        return NonceEvaluationResult(
            valid=True,
            decision=PolicyDecision.ALLOW,
            nonce_value=clean_nonce,
            mandate_id=mandate_id,
            transaction_id=transaction_id,
            record=consumed_record,
            rejection_reason=None,
            rejection_detail=None,
            evaluated_at=eval_time,
        )

    async def async_get_nonce(
        self, uow: AsyncUnitOfWork, nonce_value: str, ttl_seconds: int = 300
    ) -> NonceRecord | None:
        """Lookup nonce in database via uow.nonces."""
        clean = nonce_value.strip() if nonce_value else ""
        if not clean:
            return None
        model = await uow.nonces.get_nonce(clean)
        if model is None:
            return None
        expires_time = datetime.fromtimestamp(
            model.created_at.timestamp() + ttl_seconds, tz=timezone.utc
        )
        return NonceRecord(
            nonce_value=model.nonce,
            mandate_id=model.mandate_id,
            transaction_id=model.transaction_id,
            state=NonceState(model.status),
            issued_at=model.created_at,
            expires_at=expires_time,
            consumed_at=model.consumed_at,
        )
