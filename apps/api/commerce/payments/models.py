"""
S01.12 — Agentic Payments Core Models & Enums.

Defines provider-neutral data structures, state machines, policies, and protocol types
for Razorpay Test-Mode integration, x402 compatibility, UAP-aligned authorization,
and transaction timeline events.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class RazorpayMode(str, Enum):
    TEST = "test"
    LIVE = "live"


class PaymentState(str, Enum):
    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_razorpay_status(cls, status: str) -> PaymentState:
        s = (status or "").lower()
        if s in ("created", "issued"):
            return cls.CREATED
        elif s in ("authorized",):
            return cls.AUTHORIZED
        elif s in ("captured", "paid"):
            return cls.CAPTURED
        elif s in ("failed", "expired", "cancelled"):
            return cls.FAILED
        elif s in ("refunded",):
            return cls.REFUNDED
        return cls.UNKNOWN


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKED = "BLOCKED"


class AuthorizationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    CONSUMED = "CONSUMED"
    SUSPENDED = "SUSPENDED"


@dataclass
class AgentSpendingLimits:
    """Strict spending thresholds enforced by the deterministic payment policy engine."""

    per_transaction_limit_paise: int = 50000  # ₹500
    daily_limit_paise: int = 200000  # ₹2,000
    allowed_currencies: Set[str] = field(default_factory=lambda: {"INR"})
    allowed_categories: Set[str] = field(default_factory=lambda: {"grocery", "general", "beverage"})
    allowed_merchants: Set[str] = field(
        default_factory=set
    )  # Empty means all allowed unless scoped


@dataclass
class AgentIdentity:
    """Stable, cryptographic-bound agent identity."""

    agent_id: str
    agent_instance_id: str
    owner_id: str
    roles: List[str] = field(default_factory=lambda: ["shopping_agent"])


@dataclass
class AgentPaymentPolicy:
    """Deterministic policy configuration governing an agent's payment authority."""

    policy_id: str
    agent_id: str
    limits: AgentSpendingLimits = field(default_factory=AgentSpendingLimits)
    require_human_confirmation: bool = True
    require_verified_product: bool = True
    max_allowed_risk_level: RiskLevel = RiskLevel.MEDIUM
    allowed_providers: Set[str] = field(
        default_factory=lambda: {"razorpay", "razorpay_test", "x402", "uap_delegated"}
    )


@dataclass
class AuthorizationPolicy:
    """UAP-aligned user delegation policy granting bounded payment authority to an agent."""

    authorization_id: str
    agent_id: str
    user_id: str
    scope_merchants: List[str] = field(default_factory=list)
    max_amount_paise: int = 50000  # ₹500
    daily_limit_paise: int = 200000  # ₹2,000
    allowed_currency: str = "INR"
    category_scope: List[str] = field(default_factory=lambda: ["grocery", "general"])
    expiration_timestamp: float = field(default_factory=lambda: time.time() + 86400)
    status: AuthorizationStatus = AuthorizationStatus.ACTIVE
    token: str = field(default_factory=str)


@dataclass
class RazorpayTestOrder:
    """Representation of a Razorpay Order created in Test/Sandbox mode."""

    order_id: str
    amount_paise: int
    currency: str
    receipt: str
    status: str
    created_at: int
    notes: Dict[str, Any] = field(default_factory=dict)
    mode: RazorpayMode = RazorpayMode.TEST


@dataclass
class RazorpayPaymentDetails:
    """Representation of a Razorpay Payment entity."""

    payment_id: str
    order_id: str
    amount_paise: int
    currency: str
    status: str
    method: str
    email: str
    contact: str
    created_at: int
    notes: Dict[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None
    error_description: Optional[str] = None


@dataclass
class PaymentRequirementX402:
    """Parsed HTTP 402 Payment Requirement payload according to x402 specification."""

    resource_url: str
    amount_paise: int
    currency: str
    recipient_address: str
    network: str
    asset: str
    expiration_timestamp: float
    requirement_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentProofX402:
    """Proof of payment submitted to complete an x402-protected request."""

    requirement_hash: str
    transaction_hash: str
    signature: str
    proof_token: str
    created_at: float = field(default_factory=time.time)


@dataclass
class PaymentTimelineEvent:
    """Real-time timeline event tracing the exact lifecycle of an agentic transaction."""

    event_id: str
    timestamp: float
    stage: str
    label: str
    detail: str
    status: str = "COMPLETED"  # COMPLETED, IN_PROGRESS, FAILED, SKIPPED
    is_failed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
