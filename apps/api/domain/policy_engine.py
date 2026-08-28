"""
[S01.5 — Authorization Decision Engine]

The central authorization component of Mandate Gateway (Section 11, PROJECT_CONTEXT.md).

Core Invariant (Section 1.6):
    Zero LLM authorization.
    The LLM may reason, search, and propose a cart.
    The Gateway is the sole financial authorization authority.

Decision outcomes:
    ALLOW            → satisfy all checks, auto-execute
    STEP_UP_REQUIRED → amount exceeds mandate cap but within +10% threshold
    REJECT           → one or more mandatory checks failed (carried in RejectionReason)

No probabilistic decisions. 100% deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from apps.api.contracts.transaction import DecisionTraceResponse, StepUpDiff
from apps.api.domain.budget import DailyBudget
from apps.api.domain.budget_engine import assert_can_reserve
from apps.api.domain.cart import Cart
from apps.api.domain.mandate import BuyerMandate
from apps.api.domain.merchant import MerchantPolicy
from apps.api.domain.nonce import NonceRecord
from apps.api.domain.nonce_engine import assert_nonce_consumable
from apps.api.domain.step_up import StepUpZone
from apps.api.domain.step_up_engine import classify_step_up_zone
from apps.api.domain.types import (
    McpOperation,
    PolicyDecision,
    Region,
    RejectionReason,
)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True, slots=True)
class PolicyEvaluationResult:
    """Outcome of PolicyEngine.evaluate()."""

    decision: PolicyDecision
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    step_up_diff: StepUpDiff | None = None
    trace: DecisionTraceResponse = field(
        default_factory=lambda: DecisionTraceResponse(
            decision=PolicyDecision.REJECT,
            checks_passed=[],
            checks_failed=[],
        )
    )

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


class PolicyEngine:
    """
    Pure deterministic policy evaluation engine.

    Evaluates a proposed purchase against:
      - Buyer Mandate
      - Merchant AI Commerce Policy
      - Cart Integrity
      - Daily Budget State
      - Operation & Region Permissions
      - Expiry & TTL
      - Execution Nonce

    Pure Python — zero I/O or network dependencies.
    """

    @staticmethod
    def evaluate(  # noqa: C901
        *,
        mandate: BuyerMandate,
        merchant_policy: MerchantPolicy,
        cart: Cart,
        budget: DailyBudget | None = None,
        operation: McpOperation = McpOperation.CREATE_ORDER,
        region: Region = Region.IN,
        nonce_record: NonceRecord | None = None,
        at: datetime | None = None,
    ) -> PolicyEvaluationResult:
        """
        Evaluate all authorization checks in fixed precedence order.

        Precedence order ensures security errors fail early and cleanly:
          1. Merchant AI Commerce master switch
          2. Merchant policy active & region
          3. MCP operation permissions (blocked ops take precedence)
          4. Buyer mandate active & not expired
          5. Mandate merchant scope
          6. Mandate category scope & merchant category
          7. Currency alignment
          8. Cart integrity & total correctness
          9. Nonce validity (if provided)
          10. Autonomous execution permission
          11. Budget availability
          12. Step-up threshold & amount caps

        Returns:
            PolicyEvaluationResult containing decision, rejection details, trace.
        """
        now = at if at is not None else _utc_now()
        passed: list[str] = []
        failed: list[str] = []

        def _reject(reason: RejectionReason, detail: str) -> PolicyEvaluationResult:
            failed.append(f"{reason.value}: {detail}")
            trace = DecisionTraceResponse(
                decision=PolicyDecision.REJECT,
                checks_passed=passed,
                checks_failed=failed,
                rejection_reason=reason,
            )
            return PolicyEvaluationResult(
                decision=PolicyDecision.REJECT,
                rejection_reason=reason,
                rejection_detail=detail,
                trace=trace,
            )

        # --------------------------------------------------------------
        # 1. Merchant Policy: AI commerce master switch
        # --------------------------------------------------------------
        if not merchant_policy.ai_commerce_enabled:
            return _reject(
                RejectionReason.AI_COMMERCE_DISABLED,
                f"Merchant '{merchant_policy.merchant_id}' has disabled AI commerce.",
            )
        passed.append("MERCHANT_AI_COMMERCE_ENABLED")

        # --------------------------------------------------------------
        # 2. Merchant Policy: Expiry & Region
        # --------------------------------------------------------------
        if not merchant_policy.is_active(now):
            return _reject(
                RejectionReason.POLICY_VERSION_INVALID,
                f"Merchant policy (v{merchant_policy.policy_version}) has expired.",
            )
        passed.append("MERCHANT_POLICY_ACTIVE")

        if not merchant_policy.is_region_allowed(region):
            return _reject(
                RejectionReason.REGION_NOT_ALLOWED,
                f"Region '{region.value}' is not permitted by merchant policy.",
            )
        passed.append("MERCHANT_REGION_ALLOWED")

        # --------------------------------------------------------------
        # 3. Operation Permissions (Blocked ops take strict precedence)
        # --------------------------------------------------------------
        if operation in merchant_policy.blocked_operations:
            return _reject(
                RejectionReason.OPERATION_NOT_ALLOWED,
                f"Operation '{operation.value}' is explicitly blocked by merchant policy.",
            )
        if operation not in merchant_policy.allowed_operations:
            return _reject(
                RejectionReason.OPERATION_NOT_ALLOWED,
                f"Operation '{operation.value}' is not in merchant allowed_operations.",
            )
        passed.append("OPERATION_ALLOWED")

        # --------------------------------------------------------------
        # 4. Buyer Mandate: Active & TTL
        # --------------------------------------------------------------
        if not mandate.is_active(now):
            if now >= mandate.expires_at:
                return _reject(
                    RejectionReason.MANDATE_EXPIRED,
                    f"Buyer mandate expired at {mandate.expires_at.isoformat()}.",
                )
            return _reject(
                RejectionReason.MANDATE_NOT_ACTIVE,
                f"Buyer mandate status is '{mandate.status.value}', expected ACTIVE.",
            )
        passed.append("BUYER_MANDATE_ACTIVE")

        # --------------------------------------------------------------
        # 5. Buyer Mandate: Merchant Scope
        # --------------------------------------------------------------
        if not mandate.authorizes_merchant(cart.merchant_id):
            return _reject(
                RejectionReason.MERCHANT_NOT_IN_SCOPE,
                f"Merchant '{cart.merchant_id}' is not in mandate merchant_scope.",
            )
        passed.append("MANDATE_MERCHANT_IN_SCOPE")

        # --------------------------------------------------------------
        # 6. Category Scope (Mandate & Merchant)
        # --------------------------------------------------------------
        for item in cart.items:
            if not mandate.authorizes_category(item.category):
                return _reject(
                    RejectionReason.CATEGORY_NOT_IN_SCOPE,
                    f"Product category '{item.category}' is not in mandate category_scope.",
                )
            if not merchant_policy.is_category_allowed(item.category):
                return _reject(
                    RejectionReason.MERCHANT_CATEGORY_NOT_ALLOWED,
                    f"Product category '{item.category}' is not allowed by merchant policy.",
                )
        passed.append("CATEGORIES_ALLOWED")

        # --------------------------------------------------------------
        # 7. Currency Alignment (Mandate, Merchant, Cart)
        # --------------------------------------------------------------
        if cart.currency is not mandate.currency:
            return _reject(
                RejectionReason.CURRENCY_MISMATCH,
                f"Cart currency '{cart.currency.value}' does not match mandate currency '{mandate.currency.value}'.",
            )
        if cart.currency is not merchant_policy.currency:
            return _reject(
                RejectionReason.MERCHANT_CURRENCY_NOT_SUPPORTED,
                f"Cart currency '{cart.currency.value}' does not match "
                f"merchant currency '{merchant_policy.currency.value}'.",
            )
        passed.append("CURRENCY_MATCHED")

        # --------------------------------------------------------------
        # 8. Cart Integrity (Hash check already performed during Cart construction)
        # --------------------------------------------------------------
        if not cart.cart_hash:
            return _reject(
                RejectionReason.CART_INTEGRITY_VIOLATION,
                "Cart missing valid cart_hash digest.",
            )
        passed.append("CART_INTEGRITY_VALID")

        # --------------------------------------------------------------
        # 9. Nonce Validity (if nonce_record provided)
        # --------------------------------------------------------------
        if nonce_record is not None:
            try:
                assert_nonce_consumable(nonce_record, now)
                passed.append("NONCE_VALID")
            except Exception as ex:
                return _reject(
                    RejectionReason.NONCE_ALREADY_CONSUMED,
                    str(ex),
                )

        # --------------------------------------------------------------
        # 10. Autonomous Execution Permission
        # --------------------------------------------------------------
        if not mandate.autonomous_execution:
            return _reject(
                RejectionReason.AUTONOMOUS_EXECUTION_DISABLED,
                "Buyer mandate has autonomous_execution set to False.",
            )
        passed.append("AUTONOMOUS_EXECUTION_PERMITTED")

        # --------------------------------------------------------------
        # 11. Merchant Autonomous Purchase Limit
        # --------------------------------------------------------------
        if cart.total_paise > merchant_policy.autonomous_purchase_limit_paise:
            return _reject(
                RejectionReason.MERCHANT_AMOUNT_LIMIT_EXCEEDED,
                f"Cart total ({cart.total_paise} paise) exceeds merchant autonomous purchase limit "
                f"({merchant_policy.autonomous_purchase_limit_paise} paise).",
            )
        passed.append("MERCHANT_AMOUNT_LIMIT_OK")

        # --------------------------------------------------------------
        # 12. Daily Budget Check
        # --------------------------------------------------------------
        if budget is not None:
            try:
                assert_can_reserve(budget, cart.total_paise)
                passed.append("BUDGET_AVAILABLE")
            except Exception as ex:
                return _reject(
                    RejectionReason.BUDGET_INSUFFICIENT,
                    str(ex),
                )

        # --------------------------------------------------------------
        # 13. Step-Up & Spending Cap Classification
        # --------------------------------------------------------------
        step_up_eval = classify_step_up_zone(
            cart_total_paise=cart.total_paise,
            mandate_cap_paise=mandate.maximum_amount_paise,
            max_step_up_percent=merchant_policy.max_step_up_percent,
        )

        if step_up_eval.zone is StepUpZone.HARD_REJECT:
            return _reject(
                RejectionReason.EXCEEDS_STEP_UP_HARD_LIMIT,
                step_up_eval.reason,
            )

        if step_up_eval.zone is StepUpZone.STEP_UP_REQUIRED:
            failed.append("STEP_UP_REQUIRED")
            trace = DecisionTraceResponse(
                decision=PolicyDecision.STEP_UP_REQUIRED,
                checks_passed=passed,
                checks_failed=failed,
                step_up_diff=step_up_eval.diff,
            )
            return PolicyEvaluationResult(
                decision=PolicyDecision.STEP_UP_REQUIRED,
                step_up_diff=step_up_eval.diff,
                trace=trace,
            )

        # --------------------------------------------------------------
        # All checks passed → ALLOW
        # --------------------------------------------------------------
        passed.append("STEP_UP_NOT_REQUIRED")
        trace = DecisionTraceResponse(
            decision=PolicyDecision.ALLOW,
            checks_passed=passed,
            checks_failed=[],
        )
        return PolicyEvaluationResult(
            decision=PolicyDecision.ALLOW,
            trace=trace,
        )
