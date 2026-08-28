"""
S02.4 — Agent Step-Up Security & Binding Verification Guard.

Enforces transaction binding, blocks AI self-approval, detects post-challenge cart price tampering,
and verifies TTL active status.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from agent.stepup.errors import StepUpErrorCode, StepUpWorkflowError
from agent.stepup.types import AgentStepUpChallenge, StepUpStatus


class StepUpSecurityGuard:
    """
    Security guard enforcing step-up invariants and binding verification.
    """

    @classmethod
    def verify_approver_identity(cls, approver_id: str, agent_id: str = "") -> None:
        """
        Block AI agents from approving their own step-up challenges.

        Raises StepUpWorkflowError(AI_SELF_APPROVAL_BLOCKED) if approver is an AI agent.
        """
        if not approver_id or not approver_id.strip():
            raise StepUpWorkflowError(
                StepUpErrorCode.STEP_UP_UNAUTHORIZED_APPROVER,
                "Approver identity cannot be empty.",
            )

        norm_approver = approver_id.strip().lower()

        if agent_id and norm_approver == agent_id.strip().lower():
            raise StepUpWorkflowError(
                StepUpErrorCode.AI_SELF_APPROVAL_BLOCKED,
                f"AI Agent {agent_id!r} cannot approve its own step-up challenge.",
            )

        for ai_prefix in (
            "agent:",
            "ai:",
            "bot:",
            "llm:",
            "model:",
            "agent_",
            "assistant",
        ):
            if (
                norm_approver.startswith(ai_prefix)
                or norm_approver == "ai_agent"
                or norm_approver == "agent_assistant_01"
            ):
                raise StepUpWorkflowError(
                    StepUpErrorCode.AI_SELF_APPROVAL_BLOCKED,
                    f"Approver identity {approver_id!r} indicates an automated AI identity.",
                )

    @classmethod
    def verify_challenge_binding(
        cls,
        challenge: AgentStepUpChallenge,
        session_id: str,
        buyer_id: str,
        merchant_id: str,
        current_cart_hash: str,
        current_total_paise: int,
    ) -> None:
        """
        Verify exact challenge binding fields against current transaction state.

        Raises StepUpWorkflowError(STEP_UP_BINDING_MISMATCH) if cart items or prices were tampered with.
        """
        if challenge.session_id != session_id:
            raise StepUpWorkflowError(
                StepUpErrorCode.STEP_UP_BINDING_MISMATCH,
                f"Challenge session mismatch: expected {challenge.session_id!r}, got {session_id!r}.",
            )

        if challenge.buyer_id != buyer_id:
            raise StepUpWorkflowError(
                StepUpErrorCode.STEP_UP_BINDING_MISMATCH,
                f"Challenge buyer mismatch: expected {challenge.buyer_id!r}, got {buyer_id!r}.",
            )

        if challenge.merchant_id != merchant_id:
            raise StepUpWorkflowError(
                StepUpErrorCode.STEP_UP_BINDING_MISMATCH,
                f"Challenge merchant mismatch: expected {challenge.merchant_id!r}, got {merchant_id!r}.",
            )

        if challenge.cart_hash != current_cart_hash:
            raise StepUpWorkflowError(
                StepUpErrorCode.STEP_UP_BINDING_MISMATCH,
                f"Cart hash mismatch (post-approval cart tampering detected): "
                f"expected {challenge.cart_hash!r}, got {current_cart_hash!r}.",
            )

        if challenge.total_paise != current_total_paise:
            raise StepUpWorkflowError(
                StepUpErrorCode.STEP_UP_BINDING_MISMATCH,
                f"Price mismatch (post-approval price tampering detected): "
                f"expected {challenge.total_paise} paise, got {current_total_paise} paise.",
            )

    @classmethod
    def verify_challenge_active(
        cls,
        challenge: AgentStepUpChallenge,
        at: datetime | None = None,
    ) -> None:
        """
        Verify challenge is PENDING and not expired.
        """
        if challenge.status == StepUpStatus.EXPIRED or challenge.is_expired(at):
            raise StepUpWorkflowError(
                StepUpErrorCode.STEP_UP_CHALLENGE_EXPIRED,
                f"Challenge {challenge.challenge_id!r} has expired.",
            )

        if challenge.status != StepUpStatus.PENDING:
            raise StepUpWorkflowError(
                StepUpErrorCode.STEP_UP_ALREADY_RESOLVED,
                f"Challenge {challenge.challenge_id!r} is already in state {challenge.status.value}.",
            )

    @classmethod
    def validate_human_confirmation(
        cls,
        challenge_id: str,
        actor_id: str,
        confirmation_code: str,
    ) -> Any:
        """Validate human confirmation actor identity and return evaluation result object."""
        try:
            cls.verify_approver_identity(approver_id=actor_id)
            return type(
                "HumanConfirmationResult",
                (),
                {"is_valid": True, "reason": "APPROVED"},
            )()
        except StepUpWorkflowError as err:
            if err.code == StepUpErrorCode.AI_SELF_APPROVAL_BLOCKED:
                reason_str = "AI_SELF_APPROVAL_PROHIBITED"
            else:
                reason_str = err.code.value
            return type(
                "HumanConfirmationResult",
                (),
                {"is_valid": False, "reason": reason_str},
            )()
