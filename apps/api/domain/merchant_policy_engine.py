"""
S01.3 — Merchant Commerce Policy Evaluation Engine.

Deterministically evaluates whether a canonical CommerceIntent (and optional Cart)
is permitted by a merchant's explicitly configured MerchantPolicy.

Core Invariants:
  - Zero LLM authorization: AI cannot alter policy or grant overrides.
  - Fail Closed: Any missing, malformed, or conflicting condition returns REJECT.
  - Blocklist Precedence: Blocked operations/categories take strict precedence over allowed sets.
  - Immutability: Pure function evaluation; policy and intent are never mutated.
  - Pure Execution: Zero I/O, zero network, zero external side effects.

Does NOT evaluate mandate limits, budget availability, nonces, cart hashes, step-up, or execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from apps.api.domain.cart import Cart
from apps.api.domain.intent import CommerceIntent
from apps.api.domain.merchant import MerchantPolicy
from apps.api.domain.types import (
    McpOperation,
    PolicyDecision,
    RejectionReason,
)

if TYPE_CHECKING:
    from db.unit_of_work import AsyncUnitOfWork


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True, slots=True)
class RuleEvaluationStep:
    """Detailed trace step for an individual policy rule evaluation."""

    rule_name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class MerchantPolicyEvaluationResult:
    """
    Structured outcome of S01.3 Merchant Commerce Policy evaluation.

    Machine-readable decision trace for audit and downstream aggregation.
    """

    decision: PolicyDecision
    merchant_id: str
    policy_id: str
    policy_version: int
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    evaluated_rules: tuple[RuleEvaluationStep, ...] = field(default_factory=tuple)
    evaluated_at: datetime = field(default_factory=_utc_now)

    @property
    def is_allowed(self) -> bool:
        """Return True if decision is ALLOW."""
        return self.decision is PolicyDecision.ALLOW

    @property
    def is_step_up_required(self) -> bool:
        """Return True if decision is STEP_UP_REQUIRED."""
        return self.decision is PolicyDecision.STEP_UP_REQUIRED

    @property
    def is_rejected(self) -> bool:
        """Return True if decision is REJECT."""
        return self.decision is PolicyDecision.REJECT


class MerchantPolicyEngine:
    """
    Pure deterministic Merchant Policy Evaluator.

    Rule Order:
      1. Policy Validity & Status
      2. AI Commerce Master Switch
      3. Merchant Identity Binding
      4. MCP Operation Restrictions (Blocklist precedence)
      5. Currency Alignment
      6. Region Restrictions
      7. Category Restrictions
      8. Monetary Amount Thresholds
    """

    @classmethod
    def evaluate(
        cls,
        policy: MerchantPolicy,
        intent: CommerceIntent,
        cart: Cart | None = None,
        at: datetime | None = None,
    ) -> MerchantPolicyEvaluationResult:
        """
        Evaluate intent against policy deterministically.

        Returns:
            MerchantPolicyEvaluationResult with ALLOW or REJECT and full rule trace.
        """
        eval_time = at if at is not None else _utc_now()
        steps: list[RuleEvaluationStep] = []

        # --------------------------------------------------------------
        # Rule 1: Policy Active & Unexpired Status Check
        # --------------------------------------------------------------
        if not policy.is_active(at=eval_time):
            steps.append(
                RuleEvaluationStep(
                    rule_name="policy_active",
                    passed=False,
                    detail=f"Policy version {policy.policy_version} is expired or inactive.",
                )
            )
            return MerchantPolicyEvaluationResult(
                decision=PolicyDecision.REJECT,
                merchant_id=policy.merchant_id,
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                rejection_reason=RejectionReason.MERCHANT_POLICY_EXPIRED,
                rejection_detail=f"Merchant policy {policy.policy_id} v{policy.policy_version} is expired.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )
        steps.append(
            RuleEvaluationStep(
                rule_name="policy_active",
                passed=True,
                detail=f"Policy v{policy.policy_version} is active.",
            )
        )

        # --------------------------------------------------------------
        # Rule 2: AI Commerce Master Switch
        # --------------------------------------------------------------
        if not policy.ai_commerce_enabled:
            steps.append(
                RuleEvaluationStep(
                    rule_name="ai_commerce_enabled",
                    passed=False,
                    detail="AI commerce is disabled for this merchant.",
                )
            )
            return MerchantPolicyEvaluationResult(
                decision=PolicyDecision.REJECT,
                merchant_id=policy.merchant_id,
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                rejection_reason=RejectionReason.AI_COMMERCE_DISABLED,
                rejection_detail="Merchant policy has disabled AI commerce purchases.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )
        steps.append(
            RuleEvaluationStep(
                rule_name="ai_commerce_enabled",
                passed=True,
                detail="AI commerce is enabled.",
            )
        )

        # --------------------------------------------------------------
        # Rule 3: Merchant Identity Binding
        # --------------------------------------------------------------
        target_merchant = intent.target_merchant_id
        if target_merchant and target_merchant != policy.merchant_id:
            steps.append(
                RuleEvaluationStep(
                    rule_name="merchant_binding",
                    passed=False,
                    detail=(
                        f"Intent target merchant '{target_merchant}' "
                        f"does not match policy merchant '{policy.merchant_id}'."
                    ),
                )
            )
            return MerchantPolicyEvaluationResult(
                decision=PolicyDecision.REJECT,
                merchant_id=policy.merchant_id,
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                rejection_reason=RejectionReason.MERCHANT_MISMATCH,
                rejection_detail=(
                    f"Intent merchant '{target_merchant}' conflicts with policy merchant '{policy.merchant_id}'."
                ),
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )

        if cart and cart.merchant_id != policy.merchant_id:
            steps.append(
                RuleEvaluationStep(
                    rule_name="merchant_binding",
                    passed=False,
                    detail=(
                        f"Cart merchant '{cart.merchant_id}' "
                        f"does not match policy merchant '{policy.merchant_id}'."
                    ),
                )
            )
            return MerchantPolicyEvaluationResult(
                decision=PolicyDecision.REJECT,
                merchant_id=policy.merchant_id,
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                rejection_reason=RejectionReason.MERCHANT_MISMATCH,
                rejection_detail=(
                    f"Cart merchant '{cart.merchant_id}' conflicts with policy merchant '{policy.merchant_id}'."
                ),
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )

        steps.append(
            RuleEvaluationStep(
                rule_name="merchant_binding",
                passed=True,
                detail=f"Merchant identity '{policy.merchant_id}' verified.",
            )
        )

        # --------------------------------------------------------------
        # Rule 4: MCP Operation Restrictions (Blocklist Precedence)
        # --------------------------------------------------------------
        op_val = intent.metadata.get("operation") if intent.metadata else None
        if isinstance(op_val, str):
            try:
                requested_op = McpOperation(op_val.lower())
            except ValueError:
                requested_op = McpOperation.CREATE_ORDER
        else:
            requested_op = McpOperation.CREATE_ORDER

        # Check blocklist first (Blocklist Precedence)
        if requested_op in policy.blocked_operations:
            steps.append(
                RuleEvaluationStep(
                    rule_name="operation_allowed",
                    passed=False,
                    detail=f"Operation '{requested_op.value}' is explicitly BLOCKED by merchant policy.",
                )
            )
            return MerchantPolicyEvaluationResult(
                decision=PolicyDecision.REJECT,
                merchant_id=policy.merchant_id,
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                rejection_reason=RejectionReason.OPERATION_NOT_ALLOWED,
                rejection_detail=f"Operation '{requested_op.value}' is blocked by merchant policy.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )

        # If allowed_operations set is defined, operation MUST be in it
        if policy.allowed_operations and requested_op not in policy.allowed_operations:
            steps.append(
                RuleEvaluationStep(
                    rule_name="operation_allowed",
                    passed=False,
                    detail=f"Operation '{requested_op.value}' is not in policy allowed_operations set.",
                )
            )
            return MerchantPolicyEvaluationResult(
                decision=PolicyDecision.REJECT,
                merchant_id=policy.merchant_id,
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                rejection_reason=RejectionReason.OPERATION_NOT_ALLOWED,
                rejection_detail=f"Operation '{requested_op.value}' is not permitted by merchant policy.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )

        steps.append(
            RuleEvaluationStep(
                rule_name="operation_allowed",
                passed=True,
                detail=f"Operation '{requested_op.value}' is permitted.",
            )
        )

        # --------------------------------------------------------------
        # Rule 5: Currency Alignment
        # --------------------------------------------------------------
        if intent.currency != policy.currency:
            steps.append(
                RuleEvaluationStep(
                    rule_name="currency_allowed",
                    passed=False,
                    detail=(
                        f"Intent currency '{intent.currency.value}' "
                        f"does not match policy currency '{policy.currency.value}'."
                    ),
                )
            )
            return MerchantPolicyEvaluationResult(
                decision=PolicyDecision.REJECT,
                merchant_id=policy.merchant_id,
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                rejection_reason=RejectionReason.MERCHANT_CURRENCY_NOT_SUPPORTED,
                rejection_detail=(
                    f"Currency '{intent.currency.value}' is not supported by policy '{policy.currency.value}'."
                ),
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )
        steps.append(
            RuleEvaluationStep(
                rule_name="currency_allowed",
                passed=True,
                detail=f"Currency '{intent.currency.value}' matches policy.",
            )
        )

        # --------------------------------------------------------------
        # Rule 6: Region Restrictions
        # --------------------------------------------------------------
        if policy.allowed_regions and intent.region not in policy.allowed_regions:
            steps.append(
                RuleEvaluationStep(
                    rule_name="region_allowed",
                    passed=False,
                    detail=f"Intent region '{intent.region.value}' is not in allowed regions set.",
                )
            )
            return MerchantPolicyEvaluationResult(
                decision=PolicyDecision.REJECT,
                merchant_id=policy.merchant_id,
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                rejection_reason=RejectionReason.REGION_NOT_ALLOWED,
                rejection_detail=f"Region '{intent.region.value}' is not permitted by merchant policy.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )
        steps.append(
            RuleEvaluationStep(
                rule_name="region_allowed",
                passed=True,
                detail=f"Region '{intent.region.value}' is permitted.",
            )
        )

        # --------------------------------------------------------------
        # Rule 7: Category Restrictions
        # --------------------------------------------------------------
        if policy.allowed_categories:
            allowed_cats_lower = {c.lower() for c in policy.allowed_categories}

            # Check target category if present
            if intent.target_category and intent.target_category.lower() != "multi-category":
                if intent.target_category.lower() not in allowed_cats_lower:
                    steps.append(
                        RuleEvaluationStep(
                            rule_name="category_allowed",
                            passed=False,
                            detail=f"Category '{intent.target_category}' is not in policy allowed_categories.",
                        )
                    )
                    return MerchantPolicyEvaluationResult(
                        decision=PolicyDecision.REJECT,
                        merchant_id=policy.merchant_id,
                        policy_id=policy.policy_id,
                        policy_version=policy.policy_version,
                        rejection_reason=RejectionReason.MERCHANT_CATEGORY_NOT_ALLOWED,
                        rejection_detail=f"Category '{intent.target_category}' is not permitted by merchant policy.",
                        evaluated_rules=tuple(steps),
                        evaluated_at=eval_time,
                    )

            # Check line items if cart is provided
            if cart:
                for item in cart.items:
                    if item.category.lower() not in allowed_cats_lower:
                        steps.append(
                            RuleEvaluationStep(
                                rule_name="category_allowed",
                                passed=False,
                                detail=f"Cart item '{item.product_id}' category '{item.category}' is not allowed.",
                            )
                        )
                        return MerchantPolicyEvaluationResult(
                            decision=PolicyDecision.REJECT,
                            merchant_id=policy.merchant_id,
                            policy_id=policy.policy_id,
                            policy_version=policy.policy_version,
                            rejection_reason=RejectionReason.MERCHANT_CATEGORY_NOT_ALLOWED,
                            rejection_detail=(
                                f"Cart item category '{item.category}' is not permitted by merchant policy."
                            ),
                            evaluated_rules=tuple(steps),
                            evaluated_at=eval_time,
                        )

        steps.append(
            RuleEvaluationStep(
                rule_name="category_allowed",
                passed=True,
                detail="Category restrictions satisfied.",
            )
        )

        # --------------------------------------------------------------
        # Rule 8: Monetary Amount Thresholds
        # --------------------------------------------------------------
        eval_amount_paise = cart.total_paise if cart else (intent.max_budget_paise or 0)

        if eval_amount_paise > policy.autonomous_purchase_limit_paise:
            steps.append(
                RuleEvaluationStep(
                    rule_name="amount_within_autonomous_limit",
                    passed=False,
                    detail=(
                        f"Amount ({eval_amount_paise} paise) exceeds policy "
                        f"autonomous limit of {policy.autonomous_purchase_limit_paise} paise."
                    ),
                )
            )
            return MerchantPolicyEvaluationResult(
                decision=PolicyDecision.REJECT,
                merchant_id=policy.merchant_id,
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                rejection_reason=RejectionReason.MERCHANT_AMOUNT_LIMIT_EXCEEDED,
                rejection_detail=(
                    f"Requested amount ({eval_amount_paise} paise) exceeds merchant autonomous "
                    f"limit of {policy.autonomous_purchase_limit_paise} paise."
                ),
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )

        steps.append(
            RuleEvaluationStep(
                rule_name="amount_within_autonomous_limit",
                passed=True,
                detail=f"Amount ({eval_amount_paise} paise) is within autonomous limit.",
            )
        )

        # --------------------------------------------------------------
        # Final Decision: ALLOW
        # --------------------------------------------------------------
        return MerchantPolicyEvaluationResult(
            decision=PolicyDecision.ALLOW,
            merchant_id=policy.merchant_id,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            rejection_reason=None,
            rejection_detail=None,
            evaluated_rules=tuple(steps),
            evaluated_at=eval_time,
        )

    # -----------------------------------------------------------------------
    # Async Persistent Methods (S05.4 Domain Engine Persistence Integration)
    # -----------------------------------------------------------------------
    @classmethod
    async def async_get_active_policy(
        cls, uow: AsyncUnitOfWork, merchant_id: str
    ) -> MerchantPolicy | None:
        """Lookup active MerchantPolicy in database via uow.merchants."""
        import json

        clean_id = merchant_id.strip() if merchant_id else ""
        if not clean_id:
            return None
        model = await uow.merchants.get_active_policy(clean_id)
        if model is None:
            return None

        from apps.api.domain.types import Currency, McpOperation

        allowed_categories = frozenset(json.loads(model.allowed_categories_json or "[]"))
        allowed_ops = frozenset(
            [McpOperation(op) for op in json.loads(model.allowed_operations_json or "[]")]
        )
        blocked_ops = frozenset(
            [McpOperation(op) for op in json.loads(model.blocked_operations_json or "[]")]
        )

        version_int = int(model.policy_version) if str(model.policy_version).isdigit() else 1

        return MerchantPolicy(
            policy_id=model.id,
            merchant_id=model.merchant_id,
            policy_version=version_int,
            ai_commerce_enabled=model.active,
            currency=Currency.INR,
            allowed_categories=allowed_categories,
            autonomous_purchase_limit_paise=model.autonomous_limit_paise,
            step_up_threshold_paise=model.step_up_threshold_paise,
            max_step_up_percent=10,
            allowed_operations=allowed_ops,
            blocked_operations=blocked_ops,
        )

    @classmethod
    async def async_evaluate(
        cls,
        uow: AsyncUnitOfWork,
        merchant_id: str,
        intent: CommerceIntent,
        cart: Cart | None = None,
        at: datetime | None = None,
    ) -> MerchantPolicyEvaluationResult:
        """Fetch active policy from database and evaluate intent & cart."""
        eval_time = at if at is not None else _utc_now()
        policy = await cls.async_get_active_policy(uow, merchant_id)
        if policy is None:
            return MerchantPolicyEvaluationResult(
                decision=PolicyDecision.REJECT,
                merchant_id=merchant_id,
                policy_id="",
                policy_version=0,
                rejection_reason=RejectionReason.POLICY_VERSION_INVALID,
                rejection_detail=f"Active merchant policy for merchant {merchant_id!r} not found in database.",
                evaluated_at=eval_time,
            )
        return cls.evaluate(policy=policy, intent=intent, cart=cart, at=eval_time)
