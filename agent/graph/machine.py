"""
S02.1 — Agent State Machine Transition Engine.

Enforces deterministic, fail-closed state transitions for the Agent Graph.
"""

from __future__ import annotations

from agent.graph.errors import AgentStateTransitionError
from agent.graph.types import AgentStateEnum


class AgentStateMachine:
    """
    State machine transition validator enforcing legal agent lifecycle paths.

    Transitions from terminal states (COMPLETED, FAILED, CANCELLED, TIMED_OUT)
    are strictly prohibited.
    """

    LEGAL_TRANSITIONS: dict[AgentStateEnum, set[AgentStateEnum]] = {
        AgentStateEnum.IDLE: {
            AgentStateEnum.RECEIVING_INPUT,
            AgentStateEnum.FAILED,
            AgentStateEnum.CANCELLED,
        },
        AgentStateEnum.RECEIVING_INPUT: {
            AgentStateEnum.PLANNING,
            AgentStateEnum.FAILED,
            AgentStateEnum.CANCELLED,
            AgentStateEnum.TIMED_OUT,
        },
        AgentStateEnum.PLANNING: {
            AgentStateEnum.TOOL_REQUESTED,
            AgentStateEnum.PROPOSAL_READY,
            AgentStateEnum.COMPLETED,
            AgentStateEnum.FAILED,
            AgentStateEnum.CANCELLED,
            AgentStateEnum.TIMED_OUT,
        },
        AgentStateEnum.TOOL_REQUESTED: {
            AgentStateEnum.WAITING_FOR_TOOL,
            AgentStateEnum.FAILED,
            AgentStateEnum.CANCELLED,
            AgentStateEnum.TIMED_OUT,
        },
        AgentStateEnum.WAITING_FOR_TOOL: {
            AgentStateEnum.PROCESSING_TOOL_RESULT,
            AgentStateEnum.FAILED,
            AgentStateEnum.CANCELLED,
            AgentStateEnum.TIMED_OUT,
        },
        AgentStateEnum.PROCESSING_TOOL_RESULT: {
            AgentStateEnum.PLANNING,
            AgentStateEnum.PROPOSAL_READY,
            AgentStateEnum.FAILED,
            AgentStateEnum.CANCELLED,
            AgentStateEnum.TIMED_OUT,
        },
        AgentStateEnum.PROPOSAL_READY: {
            AgentStateEnum.WAITING_FOR_GATEWAY,
            AgentStateEnum.COMPLETED,
            AgentStateEnum.FAILED,
            AgentStateEnum.CANCELLED,
            AgentStateEnum.TIMED_OUT,
        },
        AgentStateEnum.WAITING_FOR_GATEWAY: {
            AgentStateEnum.COMPLETED,
            AgentStateEnum.FAILED,
            AgentStateEnum.CANCELLED,
            AgentStateEnum.TIMED_OUT,
        },
        # Terminal states have NO legal outgoing transitions
        AgentStateEnum.COMPLETED: set(),
        AgentStateEnum.FAILED: set(),
        AgentStateEnum.CANCELLED: set(),
        AgentStateEnum.TIMED_OUT: set(),
    }

    @classmethod
    def validate_transition(
        cls,
        from_state: AgentStateEnum,
        to_state: AgentStateEnum,
    ) -> None:
        """
        Validate whether transitioning from_state -> to_state is legal.

        Raises AgentStateTransitionError if illegal.
        """
        if from_state.is_terminal:
            raise AgentStateTransitionError(
                f"Cannot transition out of terminal state {from_state.value!r} to {to_state.value!r}."
            )

        allowed = cls.LEGAL_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise AgentStateTransitionError(
                f"Illegal state transition: {from_state.value} -> {to_state.value}. "
                f"Allowed transitions from {from_state.value}: {[s.value for s in allowed]}."
            )
