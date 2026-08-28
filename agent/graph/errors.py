"""
S02.1 — Agent Exception & Error Hierarchy.

Defines fail-closed exceptions for agent state transitions, loop limits, tool calls,
timeouts, cancellations, and security boundary violations.
"""

from __future__ import annotations


class AgentError(Exception):
    """Base exception for all Agent Runtime & Graph errors."""

    pass


class AgentStateTransitionError(AgentError):
    """Raised when an illegal or undefined state transition is attempted."""

    pass


class AgentLoopLimitExceededError(AgentError):
    """Raised when execution loop exceeds maximum configured iterations."""

    pass


class AgentToolLimitExceededError(AgentError):
    """Raised when total tool call count exceeds maximum configured tool limit."""

    pass


class AgentTimeoutError(AgentError):
    """Raised when execution runtime exceeds maximum wall-clock timeout."""

    pass


class AgentCancellationError(AgentError):
    """Raised when execution is explicitly cancelled by a cancellation signal."""

    pass


class AgentSecurityViolationError(AgentError):
    """Raised when prompt injection, authority spoofing, or invalid tool calls are detected."""

    pass


class AgentModelError(AgentError):
    """Raised when model provider output is invalid, malformed, or fails."""

    pass
