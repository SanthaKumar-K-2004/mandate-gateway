"""
S01.4 — Mandate Model & Lifecycle Engine.

Evaluates whether a buyer/actor mandate is valid for a requested commerce operation
under its explicitly configured scope, monetary bounds, and lifecycle state.

Core Invariants:
  - Zero LLM authorization: AI cannot alter mandate state, limits, or validity.
  - State Machine Enforcment: Enforces legal lifecycle transitions; terminal states
    (REVOKED, EXPIRED) cannot be reactivated.
  - Fail Closed: Any missing, expired, mismatched, or out-of-scope condition returns INVALID.
  - Immutability: Pure function evaluation; BuyerMandate is never mutated during evaluation.
  - Pure Execution: Zero I/O, zero network, zero external side effects.

Does NOT perform budget reservations, nonces, cart hashes, step-up, or payment execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from apps.api.domain.cart import Cart
from apps.api.domain.intent import CommerceIntent
from apps.api.domain.mandate import BuyerMandate
from apps.api.domain.types import (
    MandateStatus,
    RejectionReason,
)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Structured Domain Errors
# ---------------------------------------------------------------------------


class MandateLifecycleError(ValueError):
    """Base error for mandate lifecycle and state machine failures."""

    def __init__(self, message: str, code: str = "MANDATE_LIFECYCLE_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class MandateStateTransitionError(MandateLifecycleError):
    """Raised when an illegal mandate state transition is attempted."""

    def __init__(self, current_status: MandateStatus, target_status: MandateStatus) -> None:
        msg = (
            f"Illegal mandate state transition: {current_status.value} → {target_status.value}. "
            f"Terminal or invalid state path."
        )
        super().__init__(msg, code="MANDATE_ILLEGAL_TRANSITION")
        self.current_status = current_status
        self.target_status = target_status


# ---------------------------------------------------------------------------
# State Machine Legal Transitions
# ---------------------------------------------------------------------------

_MANDATE_LEGAL_TRANSITIONS: dict[MandateStatus, frozenset[MandateStatus]] = {
    MandateStatus.DRAFT: frozenset({MandateStatus.ACTIVE}),
    MandateStatus.ACTIVE: frozenset(
        {MandateStatus.SUSPENDED, MandateStatus.REVOKED, MandateStatus.EXPIRED}
    ),
    MandateStatus.SUSPENDED: frozenset(
        {MandateStatus.ACTIVE, MandateStatus.REVOKED, MandateStatus.EXPIRED}
    ),
    # Terminal states — no transitions allowed out of REVOKED or EXPIRED
    MandateStatus.REVOKED: frozenset(),
    MandateStatus.EXPIRED: frozenset(),
}


def transition_mandate(
    mandate: BuyerMandate,
    target_status: MandateStatus,
    at: datetime | None = None,
) -> BuyerMandate:
    """
    Deterministically transition mandate to target_status.

    Raises:
        MandateStateTransitionError if the transition is illegal or out of terminal state.
    """
    legal_next = _MANDATE_LEGAL_TRANSITIONS.get(mandate.status, frozenset())
    if target_status not in legal_next:
        raise MandateStateTransitionError(mandate.status, target_status)

    return mandate.model_copy(update={"status": target_status})


# Helper convenience transition functions
def activate_mandate(mandate: BuyerMandate) -> BuyerMandate:
    return transition_mandate(mandate, MandateStatus.ACTIVE)


def suspend_mandate(mandate: BuyerMandate) -> BuyerMandate:
    return transition_mandate(mandate, MandateStatus.SUSPENDED)


def resume_mandate(mandate: BuyerMandate) -> BuyerMandate:
    return transition_mandate(mandate, MandateStatus.ACTIVE)


def revoke_mandate(mandate: BuyerMandate) -> BuyerMandate:
    return transition_mandate(mandate, MandateStatus.REVOKED)


def expire_mandate(mandate: BuyerMandate) -> BuyerMandate:
    return transition_mandate(mandate, MandateStatus.EXPIRED)


# ---------------------------------------------------------------------------
# Mandate Evaluation Result DTO
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MandateRuleEvaluationStep:
    """Individual rule evaluation step trace for audit."""

    rule_name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class MandateEvaluationResult:
    """
    Outcome of S01.4 Mandate evaluation.

    Structured decision trace indicating whether the mandate permits the requested intent.
    """

    valid: bool
    mandate_id: str
    buyer_id: str
    status: MandateStatus
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    evaluated_rules: tuple[MandateRuleEvaluationStep, ...] = field(default_factory=tuple)
    evaluated_at: datetime = field(default_factory=_utc_now)

    @property
    def is_valid(self) -> bool:
        return self.valid

    @property
    def is_invalid(self) -> bool:
        return not self.valid


# ---------------------------------------------------------------------------
# Mandate Evaluation Engine
# ---------------------------------------------------------------------------


class MandateEvaluator:
    """
    Pure deterministic Buyer Mandate Evaluator.

    Rule Order:
      1. Mandate Lifecycle Status Check (Must be ACTIVE)
      2. Autonomous Execution Master Switch (Must be True)
      3. Validity Window & Expiry Check (issued_at <= at < expires_at)
      4. Buyer / Actor Identity Binding Check
      5. Merchant Scope Check (If merchant_scope non-empty)
      6. Currency Alignment Check
      7. Region Scope Check
      8. Category Scope Check (If category_scope non-empty)
      9. Monetary Single-Transaction Amount Cap Check
    """

    @classmethod
    def evaluate(  # noqa: C901
        cls,
        mandate: BuyerMandate,
        intent: CommerceIntent,
        cart: Cart | None = None,
        at: datetime | None = None,
    ) -> MandateEvaluationResult:
        """
        Evaluate proposed CommerceIntent (and optional Cart) against BuyerMandate.

        Returns:
            MandateEvaluationResult (valid=True if all scope rules pass, valid=False otherwise).
        """
        eval_time = at if at is not None else _utc_now()
        steps: list[MandateRuleEvaluationStep] = []

        # --------------------------------------------------------------
        # Rule 1: Mandate Lifecycle Status Check
        # --------------------------------------------------------------
        if mandate.status is MandateStatus.SUSPENDED:
            steps.append(
                MandateRuleEvaluationStep(
                    rule_name="mandate_status",
                    passed=False,
                    detail="Mandate is currently SUSPENDED.",
                )
            )
            return MandateEvaluationResult(
                valid=False,
                mandate_id=mandate.mandate_id,
                buyer_id=mandate.buyer_id,
                status=mandate.status,
                rejection_reason=RejectionReason.MANDATE_NOT_ACTIVE,
                rejection_detail=f"Mandate '{mandate.mandate_id}' is suspended.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )

        if mandate.status is MandateStatus.REVOKED:
            steps.append(
                MandateRuleEvaluationStep(
                    rule_name="mandate_status",
                    passed=False,
                    detail="Mandate has been REVOKED.",
                )
            )
            return MandateEvaluationResult(
                valid=False,
                mandate_id=mandate.mandate_id,
                buyer_id=mandate.buyer_id,
                status=mandate.status,
                rejection_reason=RejectionReason.MANDATE_REVOKED,
                rejection_detail=f"Mandate '{mandate.mandate_id}' has been permanently revoked.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )

        if mandate.status is MandateStatus.EXPIRED:
            steps.append(
                MandateRuleEvaluationStep(
                    rule_name="mandate_status",
                    passed=False,
                    detail="Mandate has EXPIRED.",
                )
            )
            return MandateEvaluationResult(
                valid=False,
                mandate_id=mandate.mandate_id,
                buyer_id=mandate.buyer_id,
                status=mandate.status,
                rejection_reason=RejectionReason.MANDATE_EXPIRED,
                rejection_detail=f"Mandate '{mandate.mandate_id}' is marked expired.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )

        if mandate.status is not MandateStatus.ACTIVE:
            steps.append(
                MandateRuleEvaluationStep(
                    rule_name="mandate_status",
                    passed=False,
                    detail=f"Mandate status '{mandate.status.value}' is not ACTIVE.",
                )
            )
            return MandateEvaluationResult(
                valid=False,
                mandate_id=mandate.mandate_id,
                buyer_id=mandate.buyer_id,
                status=mandate.status,
                rejection_reason=RejectionReason.MANDATE_NOT_ACTIVE,
                rejection_detail=f"Mandate '{mandate.mandate_id}' is in status '{mandate.status.value}'.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )

        steps.append(
            MandateRuleEvaluationStep(
                rule_name="mandate_status",
                passed=True,
                detail="Mandate status is ACTIVE.",
            )
        )

        # --------------------------------------------------------------
        # Rule 2: Autonomous Execution Switch
        # --------------------------------------------------------------
        if not mandate.autonomous_execution:
            steps.append(
                MandateRuleEvaluationStep(
                    rule_name="autonomous_execution",
                    passed=False,
                    detail="Autonomous execution is disabled on this mandate.",
                )
            )
            return MandateEvaluationResult(
                valid=False,
                mandate_id=mandate.mandate_id,
                buyer_id=mandate.buyer_id,
                status=mandate.status,
                rejection_reason=RejectionReason.AUTONOMOUS_EXECUTION_DISABLED,
                rejection_detail=f"Mandate '{mandate.mandate_id}' has autonomous execution disabled.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )
        steps.append(
            MandateRuleEvaluationStep(
                rule_name="autonomous_execution",
                passed=True,
                detail="Autonomous execution is enabled.",
            )
        )

        # --------------------------------------------------------------
        # Rule 3: Validity Window & Expiration Check
        # --------------------------------------------------------------
        if eval_time < mandate.issued_at:
            steps.append(
                MandateRuleEvaluationStep(
                    rule_name="validity_window",
                    passed=False,
                    detail=(
                        f"Evaluation time ({eval_time.isoformat()}) is before mandate "
                        f"issued_at ({mandate.issued_at.isoformat()})."
                    ),
                )
            )
            return MandateEvaluationResult(
                valid=False,
                mandate_id=mandate.mandate_id,
                buyer_id=mandate.buyer_id,
                status=mandate.status,
                rejection_reason=RejectionReason.MANDATE_TTL_EXPIRED,
                rejection_detail=f"Mandate '{mandate.mandate_id}' is not yet effective.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )

        if eval_time >= mandate.expires_at:
            steps.append(
                MandateRuleEvaluationStep(
                    rule_name="validity_window",
                    passed=False,
                    detail=(
                        f"Evaluation time ({eval_time.isoformat()}) is at or after mandate "
                        f"expires_at ({mandate.expires_at.isoformat()})."
                    ),
                )
            )
            return MandateEvaluationResult(
                valid=False,
                mandate_id=mandate.mandate_id,
                buyer_id=mandate.buyer_id,
                status=mandate.status,
                rejection_reason=RejectionReason.MANDATE_EXPIRED,
                rejection_detail=f"Mandate '{mandate.mandate_id}' expired at {mandate.expires_at.isoformat()}.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )

        steps.append(
            MandateRuleEvaluationStep(
                rule_name="validity_window",
                passed=True,
                detail="Mandate is within valid time window.",
            )
        )

        # --------------------------------------------------------------
        # Rule 4: Buyer / Actor Identity Binding Check
        # --------------------------------------------------------------
        if intent.buyer_id != mandate.buyer_id:
            steps.append(
                MandateRuleEvaluationStep(
                    rule_name="buyer_binding",
                    passed=False,
                    detail=(
                        f"Intent buyer_id '{intent.buyer_id}' does not match mandate "
                        f"buyer_id '{mandate.buyer_id}'."
                    ),
                )
            )
            return MandateEvaluationResult(
                valid=False,
                mandate_id=mandate.mandate_id,
                buyer_id=mandate.buyer_id,
                status=mandate.status,
                rejection_reason=RejectionReason.MANDATE_NOT_IN_SCOPE,
                rejection_detail=f"Intent buyer '{intent.buyer_id}' does not own mandate '{mandate.mandate_id}'.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )
        steps.append(
            MandateRuleEvaluationStep(
                rule_name="buyer_binding",
                passed=True,
                detail=f"Buyer identity '{mandate.buyer_id}' verified.",
            )
        )

        # --------------------------------------------------------------
        # Rule 5: Merchant Scope Check
        # --------------------------------------------------------------
        if mandate.merchant_scope:
            target_merchant = intent.target_merchant_id
            if target_merchant and not mandate.authorizes_merchant(target_merchant):
                steps.append(
                    MandateRuleEvaluationStep(
                        rule_name="merchant_scope",
                        passed=False,
                        detail=f"Target merchant '{target_merchant}' is not in mandate merchant_scope.",
                    )
                )
                return MandateEvaluationResult(
                    valid=False,
                    mandate_id=mandate.mandate_id,
                    buyer_id=mandate.buyer_id,
                    status=mandate.status,
                    rejection_reason=RejectionReason.MERCHANT_NOT_IN_SCOPE,
                    rejection_detail=f"Merchant '{target_merchant}' is outside mandate scope.",
                    evaluated_rules=tuple(steps),
                    evaluated_at=eval_time,
                )

            if cart and not mandate.authorizes_merchant(cart.merchant_id):
                steps.append(
                    MandateRuleEvaluationStep(
                        rule_name="merchant_scope",
                        passed=False,
                        detail=f"Cart merchant '{cart.merchant_id}' is not in mandate merchant_scope.",
                    )
                )
                return MandateEvaluationResult(
                    valid=False,
                    mandate_id=mandate.mandate_id,
                    buyer_id=mandate.buyer_id,
                    status=mandate.status,
                    rejection_reason=RejectionReason.MERCHANT_NOT_IN_SCOPE,
                    rejection_detail=f"Cart merchant '{cart.merchant_id}' is outside mandate scope.",
                    evaluated_rules=tuple(steps),
                    evaluated_at=eval_time,
                )

        steps.append(
            MandateRuleEvaluationStep(
                rule_name="merchant_scope",
                passed=True,
                detail="Merchant scope satisfied.",
            )
        )

        # --------------------------------------------------------------
        # Rule 6: Currency Alignment Check
        # --------------------------------------------------------------
        if intent.currency != mandate.currency:
            steps.append(
                MandateRuleEvaluationStep(
                    rule_name="currency_allowed",
                    passed=False,
                    detail=(
                        f"Intent currency '{intent.currency.value}' does not match "
                        f"mandate currency '{mandate.currency.value}'."
                    ),
                )
            )
            return MandateEvaluationResult(
                valid=False,
                mandate_id=mandate.mandate_id,
                buyer_id=mandate.buyer_id,
                status=mandate.status,
                rejection_reason=RejectionReason.CURRENCY_MISMATCH,
                rejection_detail=(
                    f"Currency '{intent.currency.value}' conflicts with "
                    f"mandate currency '{mandate.currency.value}'."
                ),
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )
        steps.append(
            MandateRuleEvaluationStep(
                rule_name="currency_allowed",
                passed=True,
                detail=f"Currency '{intent.currency.value}' matches mandate.",
            )
        )

        # --------------------------------------------------------------
        # Rule 7: Region Scope Check
        # --------------------------------------------------------------
        if mandate.allowed_regions and not mandate.authorizes_region(intent.region):
            steps.append(
                MandateRuleEvaluationStep(
                    rule_name="region_allowed",
                    passed=False,
                    detail=f"Intent region '{intent.region.value}' is not in mandate allowed_regions.",
                )
            )
            return MandateEvaluationResult(
                valid=False,
                mandate_id=mandate.mandate_id,
                buyer_id=mandate.buyer_id,
                status=mandate.status,
                rejection_reason=RejectionReason.REGION_NOT_ALLOWED,
                rejection_detail=f"Region '{intent.region.value}' is outside mandate region scope.",
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )
        steps.append(
            MandateRuleEvaluationStep(
                rule_name="region_allowed",
                passed=True,
                detail=f"Region '{intent.region.value}' is authorized.",
            )
        )

        # --------------------------------------------------------------
        # Rule 8: Category Scope Check
        # --------------------------------------------------------------
        if mandate.category_scope:
            if intent.target_category and intent.target_category.lower() != "multi-category":
                if not mandate.authorizes_category(intent.target_category):
                    steps.append(
                        MandateRuleEvaluationStep(
                            rule_name="category_scope",
                            passed=False,
                            detail=f"Category '{intent.target_category}' is not in mandate category_scope.",
                        )
                    )
                    return MandateEvaluationResult(
                        valid=False,
                        mandate_id=mandate.mandate_id,
                        buyer_id=mandate.buyer_id,
                        status=mandate.status,
                        rejection_reason=RejectionReason.CATEGORY_NOT_IN_SCOPE,
                        rejection_detail=f"Category '{intent.target_category}' is outside mandate category scope.",
                        evaluated_rules=tuple(steps),
                        evaluated_at=eval_time,
                    )

            if cart:
                for item in cart.items:
                    if not mandate.authorizes_category(item.category):
                        steps.append(
                            MandateRuleEvaluationStep(
                                rule_name="category_scope",
                                passed=False,
                                detail=(
                                    f"Cart item '{item.product_id}' category '{item.category}' "
                                    f"is not in mandate scope."
                                ),
                            )
                        )
                        return MandateEvaluationResult(
                            valid=False,
                            mandate_id=mandate.mandate_id,
                            buyer_id=mandate.buyer_id,
                            status=mandate.status,
                            rejection_reason=RejectionReason.CATEGORY_NOT_IN_SCOPE,
                            rejection_detail=f"Cart item category '{item.category}' is outside mandate scope.",
                            evaluated_rules=tuple(steps),
                            evaluated_at=eval_time,
                        )

        steps.append(
            MandateRuleEvaluationStep(
                rule_name="category_scope",
                passed=True,
                detail="Category scope satisfied.",
            )
        )

        # --------------------------------------------------------------
        # Rule 9: Monetary Single-Transaction Amount Cap Check
        # --------------------------------------------------------------
        eval_amount_paise = cart.total_paise if cart else (intent.max_budget_paise or 0)

        if not mandate.authorizes_amount(eval_amount_paise):
            steps.append(
                MandateRuleEvaluationStep(
                    rule_name="amount_within_mandate_cap",
                    passed=False,
                    detail=(
                        f"Amount ({eval_amount_paise} paise) exceeds mandate "
                        f"maximum_amount_paise of {mandate.maximum_amount_paise} paise."
                    ),
                )
            )
            return MandateEvaluationResult(
                valid=False,
                mandate_id=mandate.mandate_id,
                buyer_id=mandate.buyer_id,
                status=mandate.status,
                rejection_reason=RejectionReason.AMOUNT_EXCEEDS_MANDATE,
                rejection_detail=(
                    f"Requested amount ({eval_amount_paise} paise) exceeds mandate limit of "
                    f"{mandate.maximum_amount_paise} paise."
                ),
                evaluated_rules=tuple(steps),
                evaluated_at=eval_time,
            )

        steps.append(
            MandateRuleEvaluationStep(
                rule_name="amount_within_mandate_cap",
                passed=True,
                detail=f"Amount ({eval_amount_paise} paise) is within mandate cap.",
            )
        )

        # --------------------------------------------------------------
        # Final Decision: MANDATE VALID
        # --------------------------------------------------------------
        return MandateEvaluationResult(
            valid=True,
            mandate_id=mandate.mandate_id,
            buyer_id=mandate.buyer_id,
            status=mandate.status,
            rejection_reason=None,
            rejection_detail=None,
            evaluated_rules=tuple(steps),
            evaluated_at=eval_time,
        )
