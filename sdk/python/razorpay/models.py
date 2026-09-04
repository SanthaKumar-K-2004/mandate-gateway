"""
Razorpay Python SDK — Data Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RazorpayConfig:
    """Configuration for Razorpay Python SDK client."""

    base_url: str = "http://localhost:8000"
    api_key: str = "rzp_live_demo_token_123"
    merchant_id: str = "mer_acme_corp"
    timeout_seconds: float = 10.0


@dataclass
class TransactionResponse:
    """Represents a payment transaction response."""

    transaction_id: str
    merchant_id: str
    mandate_id: str
    amount_paise: int
    state: str
    currency: str = "INR"
    auth_decision: str = "ALLOW"
    provider_status: Optional[str] = None
    action_receipt_signature: Optional[str] = None
    raw_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MandateResponse:
    """Represents a payment mandate response."""

    mandate_id: str
    merchant_id: str
    buyer_id: str
    daily_budget_paise: int
    status: str = "ACTIVE"
    expires_at: Optional[str] = None


@dataclass
class WebhookSubscription:
    """Represents a webhook subscription record."""

    subscription_id: str
    merchant_id: str
    url: str
    events: List[str]
    status: str
    secret: Optional[str] = None
