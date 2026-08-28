"""
S02.4 — Agent Step-Up Data Contracts & Dataclasses.

Defines challenge status, human decision payloads, and step-up challenge records.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class StepUpStatus(str, Enum):
    """Step-up challenge lifecycle status."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class HumanDecisionChoice(str, Enum):
    """Human-in-the-loop decision choice."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class AgentStepUpChallenge:
    """
    Immutable representation of an active or resolved step-up challenge.
    """

    challenge_id: str
    session_id: str
    buyer_id: str
    merchant_id: str
    mandate_id: str
    cart_hash: str
    total_paise: int
    reason: str
    expires_at: datetime
    status: StepUpStatus = StepUpStatus.PENDING
    created_at: datetime = field(default_factory=_utc_now)

    def is_expired(self, at: datetime | None = None) -> bool:
        """Return True if challenge TTL has passed."""
        now = at or _utc_now()
        return now > self.expires_at


@dataclass(frozen=True, slots=True)
class AgentStepUpDecision:
    """
    Human confirmation/rejection decision payload.
    """

    challenge_id: str
    approver_id: str
    decision: HumanDecisionChoice
    timestamp: datetime = field(default_factory=_utc_now)
    signature: str | None = None
