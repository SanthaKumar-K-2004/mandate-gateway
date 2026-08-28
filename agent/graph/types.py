"""
S02.1 — Agent State & Message Type Definitions.

Defines explicit lifecycle states, message structures, and configuration boundaries
for the Agent Runtime & Graph Foundation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class AgentStateEnum(str, Enum):
    """Authoritative lifecycle states for the Agent Runtime State Machine."""

    IDLE = "IDLE"
    RECEIVING_INPUT = "RECEIVING_INPUT"
    PLANNING = "PLANNING"
    TOOL_REQUESTED = "TOOL_REQUESTED"
    WAITING_FOR_TOOL = "WAITING_FOR_TOOL"
    PROCESSING_TOOL_RESULT = "PROCESSING_TOOL_RESULT"
    PROPOSAL_READY = "PROPOSAL_READY"
    WAITING_FOR_GATEWAY = "WAITING_FOR_GATEWAY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"

    @property
    def is_terminal(self) -> bool:
        """Return True if state is terminal."""
        return self in (
            AgentStateEnum.COMPLETED,
            AgentStateEnum.FAILED,
            AgentStateEnum.CANCELLED,
            AgentStateEnum.TIMED_OUT,
        )


class AgentMessageType(str, Enum):
    """Structured message classification for agent conversation history."""

    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    TOOL_REQUEST = "TOOL_REQUEST"
    TOOL_RESULT = "TOOL_RESULT"


@dataclass(frozen=True, slots=True)
class AgentMessage:
    """Immutable conversation message in agent context history."""

    message_type: AgentMessageType
    content: str
    tool_name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class AgentStepRecord:
    """Audit record for state machine transitions within the graph."""

    step_index: int
    from_state: AgentStateEnum
    to_state: AgentStateEnum
    detail: str | None = None
    timestamp: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class AgentConfig:
    """Immutable execution limits and timeout parameters for AgentRuntime."""

    max_iterations: int = 10
    max_tool_calls: int = 5
    timeout_seconds: float = 30.0
    allow_loop_recovery: bool = False

    def __post_init__(self) -> None:
        if self.max_iterations <= 0:
            raise ValueError(f"max_iterations must be > 0, got {self.max_iterations}")
        if self.max_tool_calls < 0:
            raise ValueError(f"max_tool_calls must be >= 0, got {self.max_tool_calls}")
        if self.timeout_seconds <= 0.0:
            raise ValueError(f"timeout_seconds must be > 0.0, got {self.timeout_seconds}")
