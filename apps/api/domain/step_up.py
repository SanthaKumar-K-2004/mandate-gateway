"""
S01.1 — Step-Up Data Contracts & Approval Structures.

Data contracts representing step-up approval structures (Section 16, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique

from apps.api.contracts.transaction import StepUpDiff
from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.types import PolicyDecision, RejectionReason, StepUpZone


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@unique
class StepUpChallengeStatus(str, Enum):
    """Lifecycle states of a human step-up challenge."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class StepUpResult:
    """Outcome data structure of step-up zone evaluation."""

    zone: StepUpZone
    diff: StepUpDiff | None = None
    reason: str = ""


@dataclass(frozen=True, slots=True)
class StepUpChallengeRecord:
    """Immutable record of a Step-Up Approval Challenge bound to transaction context."""

    challenge_id: str
    mandate_id: str
    transaction_id: str
    cart_hash: str
    approved_paise: int
    proposed_paise: int
    merchant_id: str
    status: StepUpChallengeStatus = StepUpChallengeStatus.PENDING
    created_at: datetime = field(default_factory=_utc_now)
    expires_at: datetime = field(default_factory=_utc_now)
    confirmed_at: datetime | None = None
    confirmed_by: str | None = None

    def is_expired(self, at: datetime | None = None) -> bool:
        check_time = at if at is not None else _utc_now()
        return check_time >= self.expires_at


@dataclass(frozen=True, slots=True)
class TrustedConfirmation:
    """Domain representation of a verified human confirmation event."""

    challenge_id: str
    mandate_id: str
    transaction_id: str
    cart_hash: str
    proposed_paise: int
    merchant_id: str
    confirmed_by: str


@dataclass(frozen=True, slots=True)
class StepUpEvaluationResult:
    """Outcome of step-up evaluation for authorization integration."""

    valid: bool
    decision: PolicyDecision
    zone: StepUpZone
    challenge_id: str | None = None
    diff: StepUpDiff | None = None
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    evaluated_at: datetime = field(default_factory=_utc_now)

    @property
    def is_allowed(self) -> bool:
        return self.valid and self.decision == PolicyDecision.ALLOW

    def to_security_control_outcome(self) -> SecurityControlOutcome:
        """Convert result into a standardized S01.5 SecurityControlOutcome."""
        return SecurityControlOutcome(
            control_name="STEP_UP_AUTHORIZATION",
            passed=self.valid,
            decision=self.decision,
            rejection_reason=self.rejection_reason,
            detail=self.rejection_detail,
        )
