"""
S01.10 — Step-Up / Human-in-the-Loop Authorization Engine.

Implements bounded escalation algorithm and human-in-the-loop authorization boundary (Section 16, PROJECT_CONTEXT.md).

Rules:
  Zone A — Auto Execute:
    cart_total <= mandate_cap
    → AUTO_EXECUTE / ALLOW

  Zone B — Step Up Required:
    mandate_cap < cart_total <= mandate_cap * (1 + max_step_up_percent/100)
    → STEP_UP_REQUIRED
    (Requires verified human confirmation bound to exact transaction context)

  Zone C — Hard Reject:
    cart_total > mandate_cap * (1 + max_step_up_percent/100)
    → HARD_REJECT
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from apps.api.contracts.transaction import StepUpDiff
from apps.api.domain.step_up import (
    StepUpChallengeRecord,
    StepUpChallengeStatus,
    StepUpEvaluationResult,
    StepUpResult,
    TrustedConfirmation,
)
from apps.api.domain.types import PolicyDecision, RejectionReason, StepUpZone


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def classify_step_up_zone(
    *,
    cart_total_paise: int,
    mandate_cap_paise: int,
    max_step_up_percent: int = 10,
) -> StepUpResult:
    """
    Evaluate cart total against mandate spending cap to determine step-up zone.

    Args:
        cart_total_paise: Total proposed cart price in paise.
        mandate_cap_paise: Buyer mandate single-purchase cap in paise.
        max_step_up_percent: Maximum allowed price increase percentage (default 10).

    Returns:
        StepUpResult containing the zone (AUTO_EXECUTE, STEP_UP_REQUIRED, HARD_REJECT)
        and an optional StepUpDiff for Zone B.
    """
    if cart_total_paise < 0 or mandate_cap_paise < 0:
        raise ValueError("Prices cannot be negative.")

    # Zone A: cart total is within the approved cap
    if cart_total_paise <= mandate_cap_paise:
        return StepUpResult(
            zone=StepUpZone.AUTO_EXECUTE,
            reason="Cart total is within buyer mandate limit.",
        )

    # Calculate maximum step-up cap: mandate_cap * (1 + max_step_up_percent / 100)
    max_allowed_paise = mandate_cap_paise + (mandate_cap_paise * max_step_up_percent // 100)

    # Zone B: cart total exceeds cap, but is within allowed step-up threshold
    if cart_total_paise <= max_allowed_paise:
        delta_paise = cart_total_paise - mandate_cap_paise
        delta_percent = round((delta_paise / mandate_cap_paise) * 100.0, 2)
        diff = StepUpDiff(
            approved_paise=mandate_cap_paise,
            proposed_paise=cart_total_paise,
            delta_paise=delta_paise,
            delta_percent=delta_percent,
            reason=f"Cart total exceeds mandate limit by {delta_percent}%. Step-up approval required.",
        )
        return StepUpResult(
            zone=StepUpZone.STEP_UP_REQUIRED,
            diff=diff,
            reason=f"Step-up approval required (+{delta_percent}% over cap).",
        )

    # Zone C: exceeds maximum step-up threshold → hard reject
    delta_paise = cart_total_paise - mandate_cap_paise
    delta_percent = round((delta_paise / mandate_cap_paise) * 100.0, 2)
    return StepUpResult(
        zone=StepUpZone.HARD_REJECT,
        reason=(
            f"Cart total (₹{cart_total_paise / 100:,.2f}) exceeds mandate limit "
            f"(₹{mandate_cap_paise / 100:,.2f}) by {delta_percent}%, which exceeds "
            f"the maximum allowed step-up threshold of {max_step_up_percent}%."
        ),
    )


class StepUpEngine:
    """
    Thread-safe Step-Up Authorization Engine.

    Manages Step-Up Challenge lifecycle, human confirmations, and authorization verification.
    """

    def __init__(self) -> None:
        self._challenges: dict[str, StepUpChallengeRecord] = {}
        self._lock = threading.RLock()

    def create_challenge(
        self,
        mandate_id: str,
        transaction_id: str,
        cart_hash: str,
        approved_paise: int,
        proposed_paise: int,
        merchant_id: str,
        ttl_seconds: int = 300,
        at: datetime | None = None,
    ) -> StepUpChallengeRecord:
        """Create a new step-up approval challenge bound to transaction context."""
        created_time = at if at is not None else _utc_now()
        expires_time = datetime.fromtimestamp(
            created_time.timestamp() + ttl_seconds, tz=timezone.utc
        )
        cid = f"challenge-{uuid.uuid4()}"

        record = StepUpChallengeRecord(
            challenge_id=cid,
            mandate_id=mandate_id.strip(),
            transaction_id=transaction_id.strip(),
            cart_hash=cart_hash.strip().lower(),
            approved_paise=approved_paise,
            proposed_paise=proposed_paise,
            merchant_id=merchant_id.strip(),
            status=StepUpChallengeStatus.PENDING,
            created_at=created_time,
            expires_at=expires_time,
        )

        with self._lock:
            self._challenges[cid] = record
            return record

    def record_human_confirmation(
        self,
        confirmation: TrustedConfirmation,
        at: datetime | None = None,
    ) -> StepUpChallengeRecord:
        """
        Atomically record a human confirmation for a PENDING challenge under RLock.

        Raises ValueError if challenge is not found, not PENDING, expired, or context binding mismatches.
        """
        eval_time = at if at is not None else _utc_now()
        cid = confirmation.challenge_id.strip()

        with self._lock:
            record = self._challenges.get(cid)
            if record is None:
                raise ValueError(f"Step-up challenge {cid!r} not found.")

            if record.status is not StepUpChallengeStatus.PENDING:
                raise ValueError(f"Step-up challenge {cid!r} is already {record.status.value}.")

            if eval_time >= record.expires_at:
                expired_record = StepUpChallengeRecord(
                    challenge_id=record.challenge_id,
                    mandate_id=record.mandate_id,
                    transaction_id=record.transaction_id,
                    cart_hash=record.cart_hash,
                    approved_paise=record.approved_paise,
                    proposed_paise=record.proposed_paise,
                    merchant_id=record.merchant_id,
                    status=StepUpChallengeStatus.EXPIRED,
                    created_at=record.created_at,
                    expires_at=record.expires_at,
                )
                self._challenges[cid] = expired_record
                raise ValueError(f"Step-up challenge {cid!r} has expired.")

            # Validate context binding
            if record.mandate_id != confirmation.mandate_id.strip():
                raise ValueError(
                    f"Mandate binding mismatch: challenge bound to {record.mandate_id!r}, "
                    f"confirmation submitted for {confirmation.mandate_id!r}."
                )
            if record.transaction_id != confirmation.transaction_id.strip():
                raise ValueError(
                    f"Transaction binding mismatch: challenge bound to {record.transaction_id!r}, "
                    f"confirmation submitted for {confirmation.transaction_id!r}."
                )
            if record.cart_hash != confirmation.cart_hash.strip().lower():
                raise ValueError(
                    f"Cart hash binding mismatch: challenge bound to {record.cart_hash!r}, "
                    f"confirmation submitted for {confirmation.cart_hash!r}."
                )
            if record.proposed_paise != confirmation.proposed_paise:
                raise ValueError(
                    f"Amount binding mismatch: challenge bound to ₹{record.proposed_paise / 100:.2f}, "
                    f"confirmation submitted for ₹{confirmation.proposed_paise / 100:.2f}."
                )
            if record.merchant_id != confirmation.merchant_id.strip():
                raise ValueError(
                    f"Merchant binding mismatch: challenge bound to {record.merchant_id!r}, "
                    f"confirmation submitted for {confirmation.merchant_id!r}."
                )

            # Atomically approve challenge
            approved_record = StepUpChallengeRecord(
                challenge_id=record.challenge_id,
                mandate_id=record.mandate_id,
                transaction_id=record.transaction_id,
                cart_hash=record.cart_hash,
                approved_paise=record.approved_paise,
                proposed_paise=record.proposed_paise,
                merchant_id=record.merchant_id,
                status=StepUpChallengeStatus.APPROVED,
                created_at=record.created_at,
                expires_at=record.expires_at,
                confirmed_at=eval_time,
                confirmed_by=confirmation.confirmed_by.strip(),
            )
            self._challenges[cid] = approved_record
            return approved_record

    def evaluate_authorization_step_up(
        self,
        cart_total_paise: int,
        mandate_cap_paise: int,
        merchant_max_step_up_percent: int = 10,
        challenge_id: str | None = None,
        mandate_id: str | None = None,
        transaction_id: str | None = None,
        cart_hash: str | None = None,
        merchant_id: str | None = None,
        at: datetime | None = None,
    ) -> StepUpEvaluationResult:
        """
        Evaluate step-up requirements for transaction authorization.

        Zone A: AUTO_EXECUTE -> ALLOW
        Zone B: STEP_UP_REQUIRED -> Requires valid APPROVED challenge matching context.
        Zone C: HARD_REJECT -> REJECT
        """
        eval_time = at if at is not None else _utc_now()
        step_up_result = classify_step_up_zone(
            cart_total_paise=cart_total_paise,
            mandate_cap_paise=mandate_cap_paise,
            max_step_up_percent=merchant_max_step_up_percent,
        )

        if step_up_result.zone is StepUpZone.AUTO_EXECUTE:
            return StepUpEvaluationResult(
                valid=True,
                decision=PolicyDecision.ALLOW,
                zone=StepUpZone.AUTO_EXECUTE,
                evaluated_at=eval_time,
            )

        if step_up_result.zone is StepUpZone.HARD_REJECT:
            return StepUpEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                zone=StepUpZone.HARD_REJECT,
                rejection_reason=RejectionReason.EXCEEDS_STEP_UP_HARD_LIMIT,
                rejection_detail=step_up_result.reason,
                evaluated_at=eval_time,
            )

        # Zone B: STEP_UP_REQUIRED
        if not challenge_id or not challenge_id.strip():
            return StepUpEvaluationResult(
                valid=False,
                decision=PolicyDecision.STEP_UP_REQUIRED,
                zone=StepUpZone.STEP_UP_REQUIRED,
                diff=step_up_result.diff,
                rejection_reason=None,
                rejection_detail=step_up_result.reason,
                evaluated_at=eval_time,
            )

        cid = challenge_id.strip()
        with self._lock:
            record = self._challenges.get(cid)
            if record is None:
                return StepUpEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    zone=StepUpZone.STEP_UP_REQUIRED,
                    challenge_id=cid,
                    diff=step_up_result.diff,
                    rejection_reason=RejectionReason.STEP_UP_CONFIRMATION_INVALID,
                    rejection_detail=f"Step-up challenge {cid!r} not found in store.",
                    evaluated_at=eval_time,
                )

            if record.status is not StepUpChallengeStatus.APPROVED:
                return StepUpEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    zone=StepUpZone.STEP_UP_REQUIRED,
                    challenge_id=cid,
                    diff=step_up_result.diff,
                    rejection_reason=RejectionReason.STEP_UP_CONFIRMATION_INVALID,
                    rejection_detail=f"Step-up challenge {cid!r} status is {record.status.value} (must be APPROVED).",
                    evaluated_at=eval_time,
                )

            if eval_time >= record.expires_at:
                return StepUpEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    zone=StepUpZone.STEP_UP_REQUIRED,
                    challenge_id=cid,
                    diff=step_up_result.diff,
                    rejection_reason=RejectionReason.STEP_UP_CONFIRMATION_EXPIRED,
                    rejection_detail=f"Step-up challenge {cid!r} expired at {record.expires_at.isoformat()}.",
                    evaluated_at=eval_time,
                )

            # Validate context binding match
            if mandate_id and record.mandate_id != mandate_id.strip():
                return StepUpEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    zone=StepUpZone.STEP_UP_REQUIRED,
                    challenge_id=cid,
                    diff=step_up_result.diff,
                    rejection_reason=RejectionReason.STEP_UP_CONFIRMATION_INVALID,
                    rejection_detail=f"Step-up mandate mismatch (bound {record.mandate_id!r}, current {mandate_id!r}).",
                    evaluated_at=eval_time,
                )

            if transaction_id and record.transaction_id != transaction_id.strip():
                return StepUpEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    zone=StepUpZone.STEP_UP_REQUIRED,
                    challenge_id=cid,
                    diff=step_up_result.diff,
                    rejection_reason=RejectionReason.STEP_UP_CONFIRMATION_INVALID,
                    rejection_detail=(
                        f"Step-up transaction mismatch (bound {record.transaction_id!r}, current {transaction_id!r})."
                    ),
                    evaluated_at=eval_time,
                )

            if cart_hash and record.cart_hash != cart_hash.strip().lower():
                return StepUpEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    zone=StepUpZone.STEP_UP_REQUIRED,
                    challenge_id=cid,
                    diff=step_up_result.diff,
                    rejection_reason=RejectionReason.STEP_UP_CONFIRMATION_INVALID,
                    rejection_detail=f"Step-up cart hash mismatch (bound {record.cart_hash!r}, current {cart_hash!r}).",
                    evaluated_at=eval_time,
                )

            if merchant_id and record.merchant_id != merchant_id.strip():
                return StepUpEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    zone=StepUpZone.STEP_UP_REQUIRED,
                    challenge_id=cid,
                    diff=step_up_result.diff,
                    rejection_reason=RejectionReason.STEP_UP_CONFIRMATION_INVALID,
                    rejection_detail=(
                        f"Step-up merchant mismatch (bound {record.merchant_id!r}, current {merchant_id!r})."
                    ),
                    evaluated_at=eval_time,
                )

            if record.proposed_paise != cart_total_paise:
                return StepUpEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    zone=StepUpZone.STEP_UP_REQUIRED,
                    challenge_id=cid,
                    diff=step_up_result.diff,
                    rejection_reason=RejectionReason.STEP_UP_CONFIRMATION_INVALID,
                    rejection_detail=(
                        f"Step-up amount mismatch (confirmed ₹{record.proposed_paise/100:.2f}, "
                        f"proposed ₹{cart_total_paise/100:.2f})."
                    ),
                    evaluated_at=eval_time,
                )

            # All checks passed for Zone B step-up approval!
            return StepUpEvaluationResult(
                valid=True,
                decision=PolicyDecision.ALLOW,
                zone=StepUpZone.STEP_UP_REQUIRED,
                challenge_id=cid,
                diff=step_up_result.diff,
                rejection_reason=None,
                rejection_detail=None,
                evaluated_at=eval_time,
            )

    def get_challenge(self, challenge_id: str) -> StepUpChallengeRecord | None:
        """Read-only lookup of a step-up challenge record."""
        cid = challenge_id.strip() if challenge_id else ""
        with self._lock:
            return self._challenges.get(cid)
