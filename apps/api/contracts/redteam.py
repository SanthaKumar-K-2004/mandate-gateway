"""
S02.7 — Red-Team API Response Contracts.

Response schemas for `/api/redteam/*` endpoints (Section 28, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from agent.redteam.types import AttackStatus, AttackType


class RedTeamAttackResponse(BaseModel):
    """Response DTO for an individual red-team attack simulation endpoint."""

    attack_type: AttackType
    attack_name: str
    status: AttackStatus
    expected_rejection_reason: str
    actual_rejection_reason: str
    decision_trace: list[str]
    evidence: dict[str, Any]
    audit_event_id: str | None = None


class RedTeamRunAllResponse(BaseModel):
    """Response DTO for running all 8 red-team attack simulations."""

    total_attacks: int
    total_blocked: int
    total_exploited: int
    all_passed: bool
    results: list[RedTeamAttackResponse]
