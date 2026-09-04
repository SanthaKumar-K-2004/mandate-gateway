"""
S01.12 — Agentic Payment Policy Engine & Risk Classifier.

Provides deterministic, non-LLM policy evaluation and spending limit enforcement
for AI Agent transactions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from apps.api.commerce.payments.models import (
    AgentPaymentPolicy,
    AgentSpendingLimits,
    RiskLevel,
)


@dataclass
class PolicyEvaluationContext:
    """Inputs required to evaluate a payment request against agent policy & risk models."""

    agent_id: str
    request_id: str
    user_id: str
    merchant_id: str
    merchant_name: str
    category: str
    currency: str
    amount_paise: int
    provider: str
    is_product_verified: bool = True
    has_human_confirmation: bool = True
    confirmation_expired: bool = False
    authorization_token: Optional[str] = None
    is_new_merchant: bool = False
    recent_failure_count: int = 0


@dataclass
class PolicyEvaluationResult:
    """Result of a policy evaluation."""

    allowed: bool
    risk_level: RiskLevel
    reason: str
    block_code: Optional[str] = None
    policy_id: Optional[str] = None
    evaluated_at: float = field(default_factory=time.time)


class AgentPaymentPolicyEngine:
    """
    Deterministic Payment Policy Engine.

    Guarantees:
      - Strict integer spending limit enforcement.
      - Product verification requirement enforcement.
      - Mandatory human confirmation enforcement.
      - Risk classification (LOW, MEDIUM, HIGH, BLOCKED).
      - Cumulative daily limit tracking.
      - Zero LLM dynamic decision-making in financial safety critical paths.
    """

    def __init__(self, default_policy: Optional[AgentPaymentPolicy] = None) -> None:
        self.default_policy = default_policy or AgentPaymentPolicy(
            policy_id="pol_default_shopping",
            agent_id="shopping_agent_01",
            limits=AgentSpendingLimits(
                per_transaction_limit_paise=50000,  # ₹500
                daily_limit_paise=200000,  # ₹2,000
                allowed_currencies={"INR"},
                allowed_categories={"grocery", "beverage", "electronics", "general"},
            ),
            require_human_confirmation=True,
            require_verified_product=True,
            max_allowed_risk_level=RiskLevel.MEDIUM,
        )
        self._custom_policies: Dict[str, AgentPaymentPolicy] = {}
        # Cumulative daily expenditure per agent_id in paise: agent_id -> (date_str, total_paise)
        self._daily_spending: Dict[str, Dict[str, int]] = {}

    def register_policy(self, policy: AgentPaymentPolicy) -> None:
        """Register a custom policy for a specific agent_id."""
        self._custom_policies[policy.agent_id] = policy

    def get_policy(self, agent_id: str) -> AgentPaymentPolicy:
        """Retrieve policy for an agent, falling back to default policy."""
        return self._custom_policies.get(agent_id, self.default_policy)

    def _get_today_str(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def record_spending(self, agent_id: str, amount_paise: int) -> None:
        """Record executed spending for daily limit tracking."""
        today = self._get_today_str()
        if agent_id not in self._daily_spending:
            self._daily_spending[agent_id] = {}
        curr = self._daily_spending[agent_id].get(today, 0)
        self._daily_spending[agent_id][today] = curr + amount_paise

    def get_daily_spending(self, agent_id: str) -> int:
        """Retrieve total spent by agent today in paise."""
        today = self._get_today_str()
        return self._daily_spending.get(agent_id, {}).get(today, 0)

    def classify_risk(self, ctx: PolicyEvaluationContext) -> RiskLevel:
        """
        Calculates a deterministic risk level for the transaction context.
        """
        score = 0

        # Amount risk factors
        if ctx.amount_paise > 100000:  # > ₹1,000
            score += 3
        elif ctx.amount_paise > 50000:  # > ₹500
            score += 2
        elif ctx.amount_paise > 20000:  # > ₹200
            score += 1

        # Product verification risk
        if not ctx.is_product_verified:
            score += 3

        # Merchant risk
        if ctx.is_new_merchant:
            score += 2

        # Human confirmation missing/expired
        if not ctx.has_human_confirmation or ctx.confirmation_expired:
            score += 5

        # Recent failure velocity
        if ctx.recent_failure_count >= 3:
            score += 4
        elif ctx.recent_failure_count >= 1:
            score += 1

        if score >= 6:
            return RiskLevel.HIGH
        elif score >= 3:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def evaluate(self, ctx: PolicyEvaluationContext) -> PolicyEvaluationResult:
        """
        Evaluates transaction context against agent policy rules deterministically.
        Returns PolicyEvaluationResult with explicit decision and block code.
        """
        policy = self.get_policy(ctx.agent_id)
        limits = policy.limits

        # Rule 1: Product Verification Check
        if policy.require_verified_product and not ctx.is_product_verified:
            return PolicyEvaluationResult(
                allowed=False,
                risk_level=RiskLevel.HIGH,
                reason="Product state is UNVERIFIED. Autonomous purchase blocked.",
                block_code="UNVERIFIED_PRODUCT",
                policy_id=policy.policy_id,
            )

        # Rule 2: Human Confirmation Check
        if policy.require_human_confirmation:
            if not ctx.has_human_confirmation:
                return PolicyEvaluationResult(
                    allowed=False,
                    risk_level=RiskLevel.HIGH,
                    reason="Human confirmation missing. Purchase requires user authorization.",
                    block_code="HUMAN_CONFIRMATION_REQUIRED",
                    policy_id=policy.policy_id,
                )
            if ctx.confirmation_expired:
                return PolicyEvaluationResult(
                    allowed=False,
                    risk_level=RiskLevel.HIGH,
                    reason="Human confirmation token has expired. Re-authorization required.",
                    block_code="CONFIRMATION_EXPIRED",
                    policy_id=policy.policy_id,
                )

        # Rule 3: Allowed Currency Check
        if ctx.currency.upper() not in limits.allowed_currencies:
            return PolicyEvaluationResult(
                allowed=False,
                risk_level=RiskLevel.BLOCKED,
                reason=f"Currency '{ctx.currency}' is not permitted by agent policy.",
                block_code="DISALLOWED_CURRENCY",
                policy_id=policy.policy_id,
            )

        # Rule 4: Per-Transaction Limit Check
        if ctx.amount_paise > limits.per_transaction_limit_paise:
            limit_rupees = limits.per_transaction_limit_paise // 100
            amt_rupees = ctx.amount_paise / 100
            return PolicyEvaluationResult(
                allowed=False,
                risk_level=RiskLevel.HIGH,
                reason=f"Transaction amount ₹{amt_rupees:.2f} exceeds per-transaction limit ₹{limit_rupees}.",
                block_code="PER_TRANSACTION_LIMIT_EXCEEDED",
                policy_id=policy.policy_id,
            )

        # Rule 5: Daily Limit Check
        current_spent = self.get_daily_spending(ctx.agent_id)
        if (current_spent + ctx.amount_paise) > limits.daily_limit_paise:
            spent_rupees = current_spent // 100
            daily_limit_rupees = limits.daily_limit_paise // 100
            return PolicyEvaluationResult(
                allowed=False,
                risk_level=RiskLevel.HIGH,
                reason=f"Daily spending limit ₹{daily_limit_rupees} exceeded. Already spent: ₹{spent_rupees}.",
                block_code="DAILY_LIMIT_EXCEEDED",
                policy_id=policy.policy_id,
            )

        # Rule 6: Allowed Category Check
        if limits.allowed_categories and ctx.category.lower() not in limits.allowed_categories:
            return PolicyEvaluationResult(
                allowed=False,
                risk_level=RiskLevel.MEDIUM,
                reason=f"Product category '{ctx.category}' is not in allowed agent category scope.",
                block_code="DISALLOWED_CATEGORY",
                policy_id=policy.policy_id,
            )

        # Rule 7: Provider Allowed Check
        if policy.allowed_providers and ctx.provider.lower() not in policy.allowed_providers:
            return PolicyEvaluationResult(
                allowed=False,
                risk_level=RiskLevel.BLOCKED,
                reason=f"Payment provider '{ctx.provider}' is not permitted by policy.",
                block_code="DISALLOWED_PROVIDER",
                policy_id=policy.policy_id,
            )

        # Rule 8: Risk Level Check
        calculated_risk = self.classify_risk(ctx)
        risk_hierarchy = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.BLOCKED: 4,
        }
        if risk_hierarchy[calculated_risk] > risk_hierarchy[policy.max_allowed_risk_level]:
            return PolicyEvaluationResult(
                allowed=False,
                risk_level=calculated_risk,
                reason=(
                    f"Calculated risk level ({calculated_risk.value}) "
                    f"exceeds policy threshold ({policy.max_allowed_risk_level.value})."
                ),
                block_code="RISK_THRESHOLD_EXCEEDED",
                policy_id=policy.policy_id,
            )

        # Passed all deterministic policy gates
        return PolicyEvaluationResult(
            allowed=True,
            risk_level=calculated_risk,
            reason="Transaction policy evaluation passed successfully.",
            policy_id=policy.policy_id,
        )

    def evaluate_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method to evaluate payload dictionary directly."""
        ctx = PolicyEvaluationContext(
            agent_id=payload.get("agent_id", "shopping-agent"),
            request_id=payload.get("request_id", "req_demo_01"),
            user_id=payload.get("user_id", "user_demo"),
            merchant_id=payload.get("merchant_id", "merchant_cafeacme"),
            merchant_name=payload.get("merchant_name", "Cafe Acme"),
            category=payload.get("category", "grocery"),
            currency=payload.get("currency", "INR"),
            amount_paise=payload.get("amount_paise", 29900),
            provider=payload.get("provider", "razorpay"),
            is_product_verified=payload.get("product_verified", True),
            has_human_confirmation=payload.get("human_confirmed", True),
            confirmation_expired=payload.get("confirmation_expired", False),
        )
        res = self.evaluate(ctx)
        return {
            "allowed": res.allowed,
            "decision": "ALLOWED" if res.allowed else "BLOCKED",
            "risk_level": res.risk_level.value,
            "rejection_reason": res.reason,
        }
