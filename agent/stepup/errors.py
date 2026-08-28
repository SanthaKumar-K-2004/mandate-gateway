"""
S02.4 — Agent Step-Up & Human-in-the-Loop Error Codes & Exceptions.

Defines domain exceptions and structured error codes for human-in-the-loop (HITL) step-up workflow.
"""

from __future__ import annotations

from enum import Enum


class StepUpErrorCode(str, Enum):
    """Structured machine-readable error codes for step-up workflow failures."""

    STEP_UP_CHALLENGE_EXPIRED = "STEP_UP_CHALLENGE_EXPIRED"
    STEP_UP_BINDING_MISMATCH = "STEP_UP_BINDING_MISMATCH"
    STEP_UP_UNAUTHORIZED_APPROVER = "STEP_UP_UNAUTHORIZED_APPROVER"
    STEP_UP_REJECTED_BY_HUMAN = "STEP_UP_REJECTED_BY_HUMAN"
    STEP_UP_ALREADY_RESOLVED = "STEP_UP_ALREADY_RESOLVED"
    INVALID_STEP_UP_DECISION = "INVALID_STEP_UP_DECISION"
    AI_SELF_APPROVAL_BLOCKED = "AI_SELF_APPROVAL_BLOCKED"
    STEP_UP_NOT_FOUND = "STEP_UP_NOT_FOUND"


class StepUpWorkflowError(Exception):
    """Domain error raised during step-up challenge creation, resolution, or verification."""

    def __init__(self, code: StepUpErrorCode, detail: str) -> None:
        super().__init__(f"[{code.value}] {detail}")
        self.code: StepUpErrorCode = code
        self.detail: str = detail
