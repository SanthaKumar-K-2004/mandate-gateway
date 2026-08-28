"""
S02.4 — Agent Step-Up Gateway & State Machine Adapter.

Bridges AgentStepUpManager with M01 StepUpEngine and manages AgentState graph transitions.
"""

from __future__ import annotations

from typing import Optional

from agent.graph.state import AgentState
from agent.graph.types import AgentStateEnum
from agent.stepup.errors import StepUpErrorCode, StepUpWorkflowError
from agent.stepup.manager import AgentStepUpManager
from agent.stepup.types import AgentStepUpChallenge, AgentStepUpDecision, StepUpStatus
from apps.api.domain.step_up_engine import StepUpResult, classify_step_up_zone


class StepUpGatewayAdapter:
    """
    Adapter linking step-up challenges to AgentState graph state machine transitions.
    """

    @classmethod
    def evaluate_step_up_zone(
        cls,
        cart_total_paise: int,
        mandate_cap_paise: int,
        max_step_up_percent: int = 10,
    ) -> StepUpResult:
        """
        Call M01 StepUpEngine to classify zone (AUTO_EXECUTE, STEP_UP_REQUIRED, HARD_REJECT).
        """
        return classify_step_up_zone(
            cart_total_paise=cart_total_paise,
            mandate_cap_paise=mandate_cap_paise,
            max_step_up_percent=max_step_up_percent,
        )

    @classmethod
    def process_step_up_flow(
        cls,
        state: AgentState,
        step_up_manager: AgentStepUpManager,
        decision: Optional[AgentStepUpDecision] = None,
        cart_hash: str = "HASH_GENERIC",
        total_paise: int = 0,
    ) -> AgentState:
        """
        Process step-up challenge creation or decision resolution on AgentState.
        """
        active_ch = step_up_manager.get_active_challenge_for_session(state.session_id)

        if not active_ch and decision is None:
            # Create new challenge
            step_up_manager.create_challenge(
                session_id=state.session_id,
                buyer_id=state.buyer_id,
                merchant_id=state.merchant_id,
                mandate_id=state.mandate_id,
                cart_hash=cart_hash,
                total_paise=total_paise,
                reason="Purchase price exceeds autonomous mandate cap.",
            )
            state.transition_to(AgentStateEnum.WAITING_FOR_GATEWAY)
            return state

        if decision is not None:
            resolved_ch = step_up_manager.resolve_decision(
                decision=decision,
                session_id=state.session_id,
                buyer_id=state.buyer_id,
                merchant_id=state.merchant_id,
                current_cart_hash=cart_hash,
                current_total_paise=total_paise,
                agent_id=state.agent_id,
            )

            if resolved_ch.status == StepUpStatus.APPROVED:
                state.transition_to(AgentStateEnum.PROPOSAL_READY)
            else:
                state.set_error(f"Step-Up failed with status {resolved_ch.status.value}.")
                state.transition_to(AgentStateEnum.FAILED)
            return state

        if active_ch and active_ch.is_expired():
            state.set_error("Step-Up challenge expired.")
            state.transition_to(AgentStateEnum.TIMED_OUT)
            return state

        state.transition_to(AgentStateEnum.WAITING_FOR_GATEWAY)
        return state
