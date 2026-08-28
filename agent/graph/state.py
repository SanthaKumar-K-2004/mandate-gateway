"""
S02.1 — Agent State Container & Thread-Safe State Management.

Defines AgentState dataclass and context isolation mechanisms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
from typing import Any

from agent.graph.machine import AgentStateMachine
from agent.graph.types import (
    AgentMessage,
    AgentMessageType,
    AgentStateEnum,
    AgentStepRecord,
)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class AgentState:
    """
    Thread-safe, stateful agent execution context container.

    Maintains lifecycle state, conversation messages, step audit history,
    tool call counters, and generated proposal payloads.
    """

    def __init__(
        self,
        agent_id: str,
        session_id: str,
        buyer_id: str,
        merchant_id: str,
        mandate_id: str,
        initial_state: AgentStateEnum = AgentStateEnum.IDLE,
    ) -> None:
        self.agent_id: str = agent_id
        self.session_id: str = session_id
        self.buyer_id: str = buyer_id
        self.merchant_id: str = merchant_id
        self.mandate_id: str = mandate_id
        self._current_state: AgentStateEnum = initial_state
        self._messages: list[AgentMessage] = []
        self._step_history: list[AgentStepRecord] = []
        self._pending_tool_call: dict[str, Any] | None = None
        self._latest_tool_result: dict[str, Any] | None = None
        self._proposal_payload: dict[str, Any] | None = None
        self._iteration_count: int = 0
        self._tool_call_count: int = 0
        self._failure_reason: str | None = None
        self.created_at: datetime = _utc_now()
        self.updated_at: datetime = _utc_now()
        self._lock: threading.RLock = threading.RLock()

        # Record initial step
        self._record_step_internal(
            from_state=AgentStateEnum.IDLE,
            to_state=initial_state,
            detail="Agent state initialized",
        )

    @property
    def current_state(self) -> AgentStateEnum:
        with self._lock:
            return self._current_state

    @property
    def messages(self) -> list[AgentMessage]:
        with self._lock:
            return list(self._messages)

    @property
    def step_history(self) -> list[AgentStepRecord]:
        with self._lock:
            return list(self._step_history)

    @property
    def pending_tool_call(self) -> dict[str, Any] | None:
        with self._lock:
            return self._pending_tool_call.copy() if self._pending_tool_call else None

    @property
    def latest_tool_result(self) -> dict[str, Any] | None:
        with self._lock:
            return self._latest_tool_result.copy() if self._latest_tool_result else None

    @property
    def proposal_payload(self) -> dict[str, Any] | None:
        with self._lock:
            return self._proposal_payload.copy() if self._proposal_payload else None

    @property
    def iteration_count(self) -> int:
        with self._lock:
            return self._iteration_count

    @property
    def tool_call_count(self) -> int:
        with self._lock:
            return self._tool_call_count

    @property
    def failure_reason(self) -> str | None:
        with self._lock:
            return self._failure_reason

    def transition_to(self, new_state: AgentStateEnum, detail: str | None = None) -> None:
        """
        Atomically validate and execute state machine transition.

        Raises AgentStateTransitionError if transition is illegal.
        """
        with self._lock:
            AgentStateMachine.validate_transition(self._current_state, new_state)
            old_state = self._current_state
            self._current_state = new_state
            self.updated_at = _utc_now()
            self._record_step_internal(from_state=old_state, to_state=new_state, detail=detail)

    def add_message(self, message: AgentMessage) -> None:
        """Add message to conversation history with context isolation."""
        with self._lock:
            self._messages.append(message)
            self.updated_at = _utc_now()

    def set_pending_tool_call(self, tool_call: dict[str, Any]) -> None:
        """Set active pending tool request payload."""
        with self._lock:
            self._pending_tool_call = dict(tool_call)
            self.updated_at = _utc_now()

    def clear_pending_tool_call(self) -> None:
        """Clear active pending tool call."""
        with self._lock:
            self._pending_tool_call = None
            self.updated_at = _utc_now()

    def set_tool_result(self, result: dict[str, Any]) -> None:
        """Set latest completed tool result payload."""
        with self._lock:
            self._latest_tool_result = dict(result)
            self.updated_at = _utc_now()

    def set_proposal_payload(self, proposal: dict[str, Any]) -> None:
        """Set generated commerce proposal payload."""
        with self._lock:
            self._proposal_payload = dict(proposal)
            self.updated_at = _utc_now()

    def increment_iteration(self) -> int:
        """Increment and return total execution iteration count."""
        with self._lock:
            self._iteration_count += 1
            self.updated_at = _utc_now()
            return self._iteration_count

    def increment_tool_call(self) -> int:
        """Increment and return total tool invocation count."""
        with self._lock:
            self._tool_call_count += 1
            self.updated_at = _utc_now()
            return self._tool_call_count

    def set_failure_reason(self, reason: str) -> None:
        """Record explicit failure rationale."""
        with self._lock:
            self._failure_reason = reason
            self.updated_at = _utc_now()

    def _record_step_internal(
        self,
        from_state: AgentStateEnum,
        to_state: AgentStateEnum,
        detail: str | None = None,
    ) -> None:
        step_idx = len(self._step_history)
        self._step_history.append(
            AgentStepRecord(
                step_index=step_idx,
                from_state=from_state,
                to_state=to_state,
                detail=detail,
                timestamp=_utc_now(),
            )
        )
