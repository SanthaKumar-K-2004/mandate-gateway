"""
Mandate Gateway — AI Agent Domain Models
Workstream 1 — Typed data contracts for agent requests, extracted intent,
purchase plans, tool invocations, decisions, and human confirmation requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AgentRequest:
    """Represents a consumer or operator AI agent request."""

    request_id: str
    merchant_id: str
    buyer_id: str
    prompt: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AgentIntent:
    """Extracted intent from raw natural language LLM interaction."""

    intent_type: str  # e.g., 'PURCHASE_PRODUCT', 'SEARCH_ONLY', 'BUDGET_QUERY'
    product_query: str
    max_amount_paise: int
    category: str = "general"
    currency: str = "INR"
    location_requirement: str = ""
    merchant_preference: str = ""
    purchase_constraints: Dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = True

    def validate(self) -> None:
        """Fail-closed validation of AI intent."""
        if not self.intent_type or self.intent_type not in (
            "PURCHASE_PRODUCT",
            "SEARCH_ONLY",
            "BUDGET_QUERY",
            "TRANSACTION_STATUS",
        ):
            raise ValueError(f"Invalid or untrusted intent_type: '{self.intent_type}'")
        if self.max_amount_paise <= 0:
            raise ValueError(
                f"Invalid max_amount_paise: {self.max_amount_paise}. Must be positive."
            )
        if self.currency != "INR":
            raise ValueError(f"Unsupported currency: '{self.currency}'. Only INR supported.")


@dataclass
class PurchaseConstraint:
    """Strict spending & policy boundaries for AI agent purchase planning."""

    max_amount_paise: int
    allowed_merchants: List[str] = field(default_factory=list)
    currency: str = "INR"


@dataclass
class PurchasePlan:
    """Deterministic, structured purchase plan generated for human confirmation."""

    plan_id: str
    request_id: str
    merchant_id: str
    buyer_id: str
    product_id: str
    product_name: str
    amount_paise: int
    currency: str = "INR"
    product_source: str = "LIVE"  # LIVE, UNVERIFIED, STALE
    source_url: str = ""
    purchase_plan_hash: str = ""
    retrieval_timestamp: str = ""
    reasoning_summary: str = ""
    tool_provenance: List[str] = field(default_factory=list)
    requires_confirmation: bool = True
    confirmation_token: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ToolInvocation:
    """Structured record of an AI tool execution request."""

    invocation_id: str
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Structured output from an executed AI tool."""

    invocation_id: str
    tool_name: str
    success: bool
    result_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class AgentDecision:
    """Final decision output from the AI agent engine."""

    status: str  # e.g., 'UNDERSTANDING', 'PLANNING', 'AWAITING_CONFIRMATION', 'REJECTED'
    purchase_plan: Optional[PurchasePlan] = None
    explanation: str = ""
    tool_results: List[ToolResult] = field(default_factory=list)


@dataclass
class ConfirmationRequirement:
    """Human-in-the-loop payment confirmation requirement."""

    confirmation_token: str
    request_id: str
    merchant_id: str
    buyer_id: str
    amount_paise: int
    currency: str = "INR"
    expires_at: str = ""
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED
