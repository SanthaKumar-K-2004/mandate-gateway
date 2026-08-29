"""
S01.8 — Replay Protection Engine.

Enterprise-grade deterministic replay protection boundary (Section 15, PROJECT_CONTEXT.md).

Core Security Property:
  First valid use of an authorization/action identity -> ALLOW
  Second equivalent use -> REJECT (REPLAY_ATTEMPT_DETECTED)

Features:
  1. Canonical Fingerprint Hashing: SHA-256 over RFC 8785 canonical JSON derived from
     mandate_id, transaction_id, cart_hash, merchant_id.
  2. Atomic Check-and-Record: Atomic evaluation under thread synchronization lock to
     prevent race-condition double execution.
  3. Fail-Closed Security: Untrusted AI metadata, headers, or prompt injection text cannot bypass replay detection.
  4. Immutability: Once recorded, replay records cannot be deleted, reset, or modified by untrusted callers.
  5. S01.5 Integration: Direct conversion to SecurityControlOutcome with control_name="REPLAY_PROTECTION".
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from typing import TYPE_CHECKING

from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.types import PolicyDecision, RejectionReason

if TYPE_CHECKING:
    from db.unit_of_work import AsyncUnitOfWork


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def compute_replay_fingerprint(
    mandate_id: str,
    transaction_id: str,
    cart_hash: str | None = None,
    merchant_id: str | None = None,
) -> str:
    """
    Compute a deterministic canonical SHA-256 replay fingerprint digest.

    Uses RFC 8785 JSON canonicalization.
    """
    canonical_obj = {
        "cart_hash": cart_hash.strip().lower() if cart_hash else "",
        "mandate_id": mandate_id.strip(),
        "merchant_id": merchant_id.strip() if merchant_id else "",
        "transaction_id": transaction_id.strip(),
    }
    encoded = json.dumps(canonical_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ReplayRecord:
    """Immutable audit record of a consumed replay fingerprint."""

    fingerprint: str
    mandate_id: str
    transaction_id: str
    created_at: datetime = field(default_factory=_utc_now)
    expires_at: datetime | None = None

    def is_expired(self, at: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        check_time = at if at is not None else _utc_now()
        return check_time >= self.expires_at


@dataclass(frozen=True, slots=True)
class ReplayEvaluationResult:
    """Outcome of a replay protection evaluation."""

    valid: bool
    decision: PolicyDecision
    fingerprint: str
    mandate_id: str
    transaction_id: str
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    evaluated_at: datetime = field(default_factory=_utc_now)

    @property
    def is_allowed(self) -> bool:
        return self.valid and self.decision == PolicyDecision.ALLOW

    def to_security_control_outcome(self) -> SecurityControlOutcome:
        """Convert result into a standardized S01.5 SecurityControlOutcome."""
        return SecurityControlOutcome(
            control_name="REPLAY_PROTECTION",
            passed=self.valid,
            decision=self.decision,
            rejection_reason=self.rejection_reason,
            detail=self.rejection_detail,
        )


class ReplayProtectionEngine:
    """
    Thread-safe, deterministic Replay Protection Engine.

    Guarantees atomic check-and-record semantics across concurrent executions.
    """

    def __init__(self) -> None:
        self._records: dict[str, ReplayRecord] = {}
        self._lock = threading.RLock()

    def check_and_record(
        self,
        mandate_id: str,
        transaction_id: str,
        cart_hash: str | None = None,
        merchant_id: str | None = None,
        ttl_seconds: int = 86400,
        at: datetime | None = None,
    ) -> ReplayEvaluationResult:
        """
        Atomically check if action fingerprint has been used, and record it if new.

        Thread-safe under RLock.
        """
        eval_time = at if at is not None else _utc_now()

        # Reject malformed identifiers
        if not mandate_id or not mandate_id.strip():
            return ReplayEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                fingerprint="",
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                rejection_reason=RejectionReason.INVALID_TRANSACTION_STATE,
                rejection_detail="Replay check failed: mandate_id cannot be empty.",
                evaluated_at=eval_time,
            )

        if not transaction_id or not transaction_id.strip():
            return ReplayEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                fingerprint="",
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                rejection_reason=RejectionReason.INVALID_TRANSACTION_STATE,
                rejection_detail="Replay check failed: transaction_id cannot be empty.",
                evaluated_at=eval_time,
            )

        fingerprint = compute_replay_fingerprint(
            mandate_id=mandate_id,
            transaction_id=transaction_id,
            cart_hash=cart_hash,
            merchant_id=merchant_id,
        )

        with self._lock:
            existing = self._records.get(fingerprint)
            if existing is not None and not existing.is_expired(eval_time):
                return ReplayEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    fingerprint=fingerprint,
                    mandate_id=mandate_id,
                    transaction_id=transaction_id,
                    rejection_reason=RejectionReason.REPLAY_ATTEMPT_DETECTED,
                    rejection_detail=(
                        f"Replay attack blocked: Transaction/action identity {transaction_id} "
                        f"for mandate {mandate_id} (fingerprint {fingerprint[:12]}...) was previously executed."
                    ),
                    evaluated_at=eval_time,
                )

            # Record new replay fingerprint atomically
            expires_at = (
                datetime.fromtimestamp(eval_time.timestamp() + ttl_seconds, tz=timezone.utc)
                if ttl_seconds > 0
                else None
            )

            record = ReplayRecord(
                fingerprint=fingerprint,
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                created_at=eval_time,
                expires_at=expires_at,
            )
            self._records[fingerprint] = record

            return ReplayEvaluationResult(
                valid=True,
                decision=PolicyDecision.ALLOW,
                fingerprint=fingerprint,
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                rejection_reason=None,
                rejection_detail=None,
                evaluated_at=eval_time,
            )

    def is_replayed(
        self,
        mandate_id: str,
        transaction_id: str,
        cart_hash: str | None = None,
        merchant_id: str | None = None,
        at: datetime | None = None,
    ) -> bool:
        """Return True if the specified fingerprint has already been recorded and is active."""
        fingerprint = compute_replay_fingerprint(
            mandate_id=mandate_id,
            transaction_id=transaction_id,
            cart_hash=cart_hash,
            merchant_id=merchant_id,
        )
        eval_time = at if at is not None else _utc_now()
        with self._lock:
            record = self._records.get(fingerprint)
            return record is not None and not record.is_expired(eval_time)

    def record_count(self) -> int:
        """Return total number of active replay records in memory."""
        with self._lock:
            return len(self._records)

    # -----------------------------------------------------------------------
    # Async Persistent Methods (S05.4 Domain Engine Persistence Integration)
    # -----------------------------------------------------------------------

    async def async_check_and_record(
        self,
        uow: AsyncUnitOfWork,
        mandate_id: str,
        transaction_id: str,
        cart_hash: str | None = None,
        merchant_id: str | None = None,
        ttl_seconds: int = 86400,
        at: datetime | None = None,
    ) -> ReplayEvaluationResult:
        """
        Atomically check and record replay protection fingerprint in database via uow.replay.
        """
        eval_time = at if at is not None else _utc_now()

        if not mandate_id or not mandate_id.strip():
            return ReplayEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                fingerprint="",
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                rejection_reason=RejectionReason.INVALID_TRANSACTION_STATE,
                rejection_detail="Replay check failed: mandate_id cannot be empty.",
                evaluated_at=eval_time,
            )

        if not transaction_id or not transaction_id.strip():
            return ReplayEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                fingerprint="",
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                rejection_reason=RejectionReason.INVALID_TRANSACTION_STATE,
                rejection_detail="Replay check failed: transaction_id cannot be empty.",
                evaluated_at=eval_time,
            )

        fingerprint = compute_replay_fingerprint(
            mandate_id=mandate_id,
            transaction_id=transaction_id,
            cart_hash=cart_hash,
            merchant_id=merchant_id,
        )

        is_replayed = await uow.replay.is_fingerprint_replayed(
            fingerprint, ttl_seconds=ttl_seconds, at=eval_time
        )
        if is_replayed:
            return ReplayEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                fingerprint=fingerprint,
                mandate_id=mandate_id,
                transaction_id=transaction_id,
                rejection_reason=RejectionReason.REPLAY_ATTEMPT_DETECTED,
                rejection_detail=(
                    f"Replay attack blocked: Transaction/action identity {transaction_id} "
                    f"for mandate {mandate_id} (fingerprint {fingerprint[:12]}...) was previously executed."
                ),
                evaluated_at=eval_time,
            )

        model = await uow.replay.record_replay_fingerprint(
            fingerprint=fingerprint,
            transaction_id=transaction_id,
            created_at=eval_time,
        )

        record = ReplayRecord(
            fingerprint=model.fingerprint,
            mandate_id=mandate_id,
            transaction_id=model.transaction_id,
            created_at=model.created_at,
            expires_at=datetime.fromtimestamp(eval_time.timestamp() + ttl_seconds, tz=timezone.utc),
        )

        with self._lock:
            self._records[fingerprint] = record

        return ReplayEvaluationResult(
            valid=True,
            decision=PolicyDecision.ALLOW,
            fingerprint=fingerprint,
            mandate_id=mandate_id,
            transaction_id=transaction_id,
            rejection_reason=None,
            rejection_detail=None,
            evaluated_at=eval_time,
        )
