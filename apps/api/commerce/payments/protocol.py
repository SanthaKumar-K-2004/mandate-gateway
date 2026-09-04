"""
S01.12 — Agentic Payment Protocol Abstraction & Provider Adapters.

Defines the unified AgentPaymentProtocol interface and adapters for Razorpay,
x402, and UAP-aligned authorization models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from apps.api.commerce.payments.models import (
    RazorpayMode,
    RiskLevel,
)

from apps.api.commerce.payments.policy import (
    AgentPaymentPolicyEngine,
    PolicyEvaluationContext,
    PolicyEvaluationResult,
)
from apps.api.commerce.payments.razorpay_client import RazorpayClient
from apps.api.commerce.payments.uap import UAPAuthorizationLayer
from apps.api.commerce.payments.x402 import X402PaymentAdapter


class AgentPaymentProtocolAdapter(ABC):
    """Abstract interface for protocol-level payment capability adapters."""

    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Name of the payment protocol."""

    @abstractmethod
    def evaluate_authorization(
        self, ctx: PolicyEvaluationContext, auth_token: Optional[str] = None
    ) -> PolicyEvaluationResult:
        """Evaluate if the payment request is authorized under policy & protocol rules."""

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return capability metadata for this protocol adapter."""


class RazorpayPaymentProtocolAdapter(AgentPaymentProtocolAdapter):
    """Protocol adapter wrapping Razorpay Test/Live mode connector."""

    def __init__(self, client: RazorpayClient, policy_engine: AgentPaymentPolicyEngine) -> None:
        self.client = client
        self.policy_engine = policy_engine

    @property
    def protocol_name(self) -> str:
        return "razorpay_test" if self.client.mode == RazorpayMode.TEST else "razorpay_live"

    def evaluate_authorization(
        self, ctx: PolicyEvaluationContext, auth_token: Optional[str] = None
    ) -> PolicyEvaluationResult:
        # Override provider name to match protocol
        ctx.provider = self.protocol_name
        return self.policy_engine.evaluate(ctx)

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "protocol": self.protocol_name,
            "provider": "Razorpay",
            "mode": self.client.mode.value,
            "reality": "SANDBOX" if self.client.mode == RazorpayMode.TEST else "LIVE",
            "capability": (
                "TEST_PAYMENT" if self.client.mode == RazorpayMode.TEST else "PRODUCTION_PAYMENT"
            ),
            "real_money": (
                False if self.client.mode == RazorpayMode.TEST else self.client.is_configured
            ),
            "configured": self.client.is_configured,
            "supports_webhooks": True,
            "supports_signature_verification": True,
        }


class X402PaymentProtocolAdapter(AgentPaymentProtocolAdapter):
    """Protocol adapter wrapping x402 HTTP Payment Required capabilities."""

    def __init__(
        self, x402_adapter: X402PaymentAdapter, policy_engine: AgentPaymentPolicyEngine
    ) -> None:
        self.x402 = x402_adapter
        self.policy_engine = policy_engine

    @property
    def protocol_name(self) -> str:
        return "x402"

    def evaluate_authorization(
        self, ctx: PolicyEvaluationContext, auth_token: Optional[str] = None
    ) -> PolicyEvaluationResult:
        ctx.provider = "x402"
        return self.policy_engine.evaluate(ctx)

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "protocol": "x402",
            "provider": "HTTP 402 Adapter",
            "mode": "protocol_compatible",
            "reality": "PROTOCOL_COMPATIBLE",
            "capability": "HTTP_402_PAYMENT_PROOFS",
            "real_money": False,
            "configured": True,
            "supports_webhooks": False,
            "supports_signature_verification": True,
        }


class UAPPaymentProtocolAdapter(AgentPaymentProtocolAdapter):
    """Protocol adapter wrapping UAP-aligned delegated authorization layer."""

    def __init__(
        self, uap_layer: UAPAuthorizationLayer, policy_engine: AgentPaymentPolicyEngine
    ) -> None:
        self.uap = uap_layer
        self.policy_engine = policy_engine

    @property
    def protocol_name(self) -> str:
        return "uap_delegated"

    def evaluate_authorization(
        self, ctx: PolicyEvaluationContext, auth_token: Optional[str] = None
    ) -> PolicyEvaluationResult:
        if not auth_token:
            return PolicyEvaluationResult(
                allowed=False,
                risk_level=RiskLevel.HIGH,
                reason="Missing UAP delegation token.",
                block_code="MISSING_UAP_TOKEN",
            )

        try:
            auth_policy = self.uap.validate_authorization(
                token_or_id=auth_token,
                agent_id=ctx.agent_id,
                merchant_id=ctx.merchant_id,
                category=ctx.category,
                amount_paise=ctx.amount_paise,
            )
        except Exception as err:
            return PolicyEvaluationResult(
                allowed=False,
                risk_level=RiskLevel.HIGH,
                reason=str(err),
                block_code="UAP_VALIDATION_FAILED",
            )

        ctx.provider = "uap_delegated"
        res = self.policy_engine.evaluate(ctx)
        if res.allowed:
            res.policy_id = auth_policy.authorization_id
        return res

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "protocol": "uap_delegated",
            "provider": "UAP Delegated Authority",
            "mode": "uap_aligned",
            "reality": "DELEGATED_AUTHORIZATION",
            "capability": "DELEGATED_SPENDING_LIMITS",
            "real_money": False,
            "configured": True,
            "supports_webhooks": False,
            "supports_signature_verification": True,
        }
