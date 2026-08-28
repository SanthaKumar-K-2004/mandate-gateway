"""
S02.7 — Red-Team Chaos Lab & Adversarial Security Data Contracts.

Defines AttackType, AttackStatus, and structured simulation result models
for Section 21 / Module 16 of PROJECT_CONTEXT.md.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from apps.api.domain.types import RejectionReason


class AttackType(str, Enum):
    """
    Mandatory 8 Red-Team Attack Vectors (Module 16, PROJECT_CONTEXT.md).
    """

    PROMPT_INJECTION = "prompt_injection"
    CART_TAMPER = "cart_tamper"
    NONCE_REPLAY = "replay"
    DOUBLE_SPEND = "double_spend"
    TIMEOUT_RETRY = "timeout"
    EXPIRED_MANDATE = "expired_mandate"
    MERCHANT_POLICY = "merchant_policy"
    UNAUTHORIZED_TOOL = "unauthorized_tool"


class AttackStatus(str, Enum):
    """
    Status outcome of a red-team security attack simulation.
    All attacks MUST result in BLOCKED for security compliance.
    """

    BLOCKED = "BLOCKED"
    EXPLOITED = "EXPLOITED"


class RedTeamAttackRequest(BaseModel):
    """Configuration options for initiating a red-team attack simulation."""

    attack_type: AttackType
    target_merchant_id: str | None = Field(default="merchant_acme")
    target_mandate_id: str | None = Field(default="mandate_buyer_1")
    custom_payload: dict[str, Any] = Field(default_factory=dict)


class RedTeamAttackResult(BaseModel):
    """
    Structured forensic result returned after executing a red-team attack simulation.
    """

    model_config = {"frozen": True}

    attack_type: AttackType
    attack_name: str
    status: AttackStatus = Field(
        ...,
        description="Must be BLOCKED for security compliance. EXPLOITED indicates a failure.",
    )
    expected_rejection_reason: str
    actual_rejection_reason: str
    decision_trace: list[str] = Field(
        default_factory=list,
        description="Step-by-step audit decision trace of why the attack was blocked.",
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Forensic metadata proving the boundary blocked the attack.",
    )
    audit_event_id: str | None = Field(
        default=None,
        description="Linked AuditEvent ID from the audit ledger.",
    )
