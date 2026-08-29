"""
S02.4 — Agent Step-Up Lifecycle & Challenge Manager.

Thread-safe manager for creating, tracking, and resolving human-in-the-loop step-up challenges.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from agent.stepup.errors import StepUpErrorCode, StepUpWorkflowError
from agent.stepup.observability import StepUpAuditLogger
from agent.stepup.security import StepUpSecurityGuard
from agent.stepup.types import (
    AgentStepUpChallenge,
    AgentStepUpDecision,
    HumanDecisionChoice,
    StepUpStatus,
)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class AgentStepUpManager:
    """
    Enterprise Step-Up Lifecycle Manager.

    Security Guarantees:
    1. Thread-safe RLock synchronization.
    2. Enforces TTL expiration.
    3. Blocks AI self-approval attempts.
    4. Detects post-challenge cart price or item tampering.
    """

    def __init__(self) -> None:
        self._challenges: Dict[str, AgentStepUpChallenge] = {}
        # Key: session_id -> challenge_id
        self._session_index: Dict[str, str] = {}
        self._lock: threading.RLock = threading.RLock()

    def create_challenge(
        self,
        session_id: str,
        buyer_id: str,
        merchant_id: str,
        mandate_id: str,
        cart_hash: str,
        total_paise: int,
        reason: str = "Total price exceeds autonomous threshold.",
        ttl_seconds: float = 300.0,
    ) -> AgentStepUpChallenge:
        """
        Create and record an active PENDING step-up challenge.
        """
        with self._lock:
            cid = f"stepup_{_new_uuid()[:8]}"
            now = _utc_now()
            expires = now + timedelta(seconds=ttl_seconds)

            challenge = AgentStepUpChallenge(
                challenge_id=cid,
                session_id=session_id,
                buyer_id=buyer_id,
                merchant_id=merchant_id,
                mandate_id=mandate_id,
                cart_hash=cart_hash,
                total_paise=total_paise,
                reason=reason,
                expires_at=expires,
                status=StepUpStatus.PENDING,
                created_at=now,
            )

            self._challenges[cid] = challenge
            self._session_index[session_id] = cid

            StepUpAuditLogger.log_event("created", challenge_id=cid, session_id=session_id)
            return challenge

    def get_challenge(self, challenge_id: str) -> Optional[AgentStepUpChallenge]:
        """Look up challenge by ID."""
        with self._lock:
            ch = self._challenges.get(challenge_id)
            if ch and ch.status == StepUpStatus.PENDING and ch.is_expired():
                # Lazy expire
                expired_ch = AgentStepUpChallenge(
                    challenge_id=ch.challenge_id,
                    session_id=ch.session_id,
                    buyer_id=ch.buyer_id,
                    merchant_id=ch.merchant_id,
                    mandate_id=ch.mandate_id,
                    cart_hash=ch.cart_hash,
                    total_paise=ch.total_paise,
                    reason=ch.reason,
                    expires_at=ch.expires_at,
                    status=StepUpStatus.EXPIRED,
                    created_at=ch.created_at,
                )
                self._challenges[challenge_id] = expired_ch
                StepUpAuditLogger.log_event(
                    "expired", challenge_id=challenge_id, session_id=ch.session_id
                )
                return expired_ch
            return ch

    def get_active_challenge_for_session(self, session_id: str) -> Optional[AgentStepUpChallenge]:
        """Look up active challenge for session."""
        with self._lock:
            cid = self._session_index.get(session_id)
            if not cid:
                return None
            return self.get_challenge(cid)

    def resolve_decision(
        self,
        decision: AgentStepUpDecision,
        session_id: str,
        buyer_id: str,
        merchant_id: str,
        current_cart_hash: str,
        current_total_paise: int,
        agent_id: str = "",
    ) -> AgentStepUpChallenge:
        """
        Evaluate and resolve human step-up decision under strict security bounds.
        """
        with self._lock:
            # 1. Retrieve Challenge
            ch = self.get_challenge(decision.challenge_id)
            if not ch:
                StepUpAuditLogger.log_event(
                    "rejected",
                    challenge_id=decision.challenge_id,
                    session_id=session_id,
                    error_code=StepUpErrorCode.STEP_UP_NOT_FOUND,
                    detail="Challenge ID not found.",
                )
                raise StepUpWorkflowError(
                    StepUpErrorCode.STEP_UP_NOT_FOUND,
                    f"Step-up challenge {decision.challenge_id!r} not found.",
                )

            # 2. Security Guard Checks
            try:
                StepUpSecurityGuard.verify_approver_identity(decision.approver_id, agent_id)
            except StepUpWorkflowError as swe:
                if swe.code == StepUpErrorCode.AI_SELF_APPROVAL_BLOCKED:
                    StepUpAuditLogger.log_event(
                        "ai_self_approval_blocked",
                        challenge_id=ch.challenge_id,
                        session_id=session_id,
                        error_code=swe.code,
                        detail=swe.detail,
                    )
                raise

            try:
                StepUpSecurityGuard.verify_challenge_binding(
                    ch, session_id, buyer_id, merchant_id, current_cart_hash, current_total_paise
                )
            except StepUpWorkflowError as swe:
                StepUpAuditLogger.log_event(
                    "tamper_detected",
                    challenge_id=ch.challenge_id,
                    session_id=session_id,
                    error_code=swe.code,
                    detail=swe.detail,
                )
                raise

            # 3. Check Active Status
            StepUpSecurityGuard.verify_challenge_active(ch)

            # 4. Resolve Decision
            if decision.decision == HumanDecisionChoice.APPROVE:
                resolved_ch = AgentStepUpChallenge(
                    challenge_id=ch.challenge_id,
                    session_id=ch.session_id,
                    buyer_id=ch.buyer_id,
                    merchant_id=ch.merchant_id,
                    mandate_id=ch.mandate_id,
                    cart_hash=ch.cart_hash,
                    total_paise=ch.total_paise,
                    reason=ch.reason,
                    expires_at=ch.expires_at,
                    status=StepUpStatus.APPROVED,
                    created_at=ch.created_at,
                )
                self._challenges[ch.challenge_id] = resolved_ch
                StepUpAuditLogger.log_event(
                    "approved", challenge_id=ch.challenge_id, session_id=session_id
                )
                return resolved_ch
            elif decision.decision == HumanDecisionChoice.REJECT:
                resolved_ch = AgentStepUpChallenge(
                    challenge_id=ch.challenge_id,
                    session_id=ch.session_id,
                    buyer_id=ch.buyer_id,
                    merchant_id=ch.merchant_id,
                    mandate_id=ch.mandate_id,
                    cart_hash=ch.cart_hash,
                    total_paise=ch.total_paise,
                    reason=ch.reason,
                    expires_at=ch.expires_at,
                    status=StepUpStatus.REJECTED,
                    created_at=ch.created_at,
                )
                self._challenges[ch.challenge_id] = resolved_ch
                StepUpAuditLogger.log_event(
                    "rejected", challenge_id=ch.challenge_id, session_id=session_id
                )
                return resolved_ch
            else:
                raise StepUpWorkflowError(
                    StepUpErrorCode.INVALID_STEP_UP_DECISION,
                    f"Unknown human decision choice: {decision.decision!r}.",
                )
