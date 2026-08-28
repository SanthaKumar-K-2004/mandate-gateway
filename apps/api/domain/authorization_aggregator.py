"""
S01.5 — Authorization Aggregation Engine.

Definitive authorization decision aggregator for Mandate Gateway (Section 11, PROJECT_CONTEXT.md).

Core Mandate:
  "Given the independently evaluated security controls, is this commerce action currently authorized?"

Rules:
  1. Unanimous Consent Rule: ALLOW iff ALL security controls evaluate to ALLOW.
  2. Short-Circuit Precedence: Any single REJECT outcome immediately short-circuits to REJECT.
  3. Precedence Order:
     Mandate Scope & Lifecycle -> Merchant Commerce Policy -> Cart Integrity ->
     Budget Reservation -> Replay Protection -> Nonce Validation -> Step-Up Classification.
  4. Missing Control Result: Any missing or UNKNOWN control result fails closed (REJECT).
  5. AI Claim Invariance: Natural language AI text ("approved", "override") is strictly ignored.
  6. Pure Function: Zero I/O, zero network, zero state mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from apps.api.contracts.transaction import StepUpDiff
from apps.api.domain.authorization import AuthorizationDecision
from apps.api.domain.mandate_lifecycle import MandateEvaluationResult
from apps.api.domain.merchant_policy_engine import MerchantPolicyEvaluationResult
from apps.api.domain.types import (
    PolicyDecision,
    RejectionReason,
)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True, slots=True)
class SecurityControlOutcome:
    """Standardized evaluation outcome from an individual security control."""

    control_name: str
    passed: bool
    decision: PolicyDecision
    rejection_reason: RejectionReason | None = None
    detail: str | None = None
    step_up_diff: StepUpDiff | None = None

    @classmethod
    def from_mandate(cls, res: MandateEvaluationResult) -> SecurityControlOutcome:
        return cls(
            control_name="MANDATE_SCOPE_LIFECYCLE",
            passed=res.valid,
            decision=PolicyDecision.ALLOW if res.valid else PolicyDecision.REJECT,
            rejection_reason=res.rejection_reason,
            detail=res.rejection_detail,
        )

    @classmethod
    def from_merchant_policy(cls, res: MerchantPolicyEvaluationResult) -> SecurityControlOutcome:
        return cls(
            control_name="MERCHANT_COMMERCE_POLICY",
            passed=res.is_allowed or res.is_step_up_required,
            decision=res.decision,
            rejection_reason=res.rejection_reason,
            detail=res.rejection_detail,
            step_up_diff=getattr(res, "step_up_diff", None),
        )


@dataclass(frozen=True, slots=True)
class AuthorizationAggregationInput:
    """Input payload containing outcomes from all independent security controls."""

    mandate_outcome: SecurityControlOutcome | MandateEvaluationResult | None
    merchant_policy_outcome: SecurityControlOutcome | MerchantPolicyEvaluationResult | None
    cart_integrity_outcome: SecurityControlOutcome | None
    budget_outcome: SecurityControlOutcome | None = None
    replay_outcome: SecurityControlOutcome | None = None
    nonce_outcome: SecurityControlOutcome | None = None
    step_up_outcome: SecurityControlOutcome | None = None


@dataclass(frozen=True, slots=True)
class AggregatedAuthorizationResult:
    """Definitive result produced by AuthorizationAggregator."""

    decision: PolicyDecision
    request_id: str
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    step_up_diff: StepUpDiff | None = None
    checks_passed: tuple[str, ...] = field(default_factory=tuple)
    checks_failed: tuple[str, ...] = field(default_factory=tuple)
    evaluated_at: datetime = field(default_factory=_utc_now)

    @property
    def is_allowed(self) -> bool:
        return self.decision is PolicyDecision.ALLOW

    @property
    def is_step_up_required(self) -> bool:
        return self.decision is PolicyDecision.STEP_UP_REQUIRED

    @property
    def is_rejected(self) -> bool:
        return self.decision is PolicyDecision.REJECT

    def to_authorization_decision(
        self,
        decision_id: str | None = None,
        transaction_id: str | None = None,
        nonce: str | None = None,
    ) -> AuthorizationDecision:
        """Convert result to domain AuthorizationDecision model."""
        return AuthorizationDecision(
            decision_id=decision_id or f"dec-{self.request_id}",
            request_id=self.request_id,
            transaction_id=transaction_id,
            decision=self.decision,
            rejection_reason=self.rejection_reason,
            rejection_detail=self.rejection_detail,
            step_up_diff=self.step_up_diff,
            checks_passed=self.checks_passed,
            checks_failed=self.checks_failed,
            nonce=nonce,
            created_at=self.evaluated_at,
        )


class AuthorizationAggregator:
    """
    Pure deterministic authorization aggregator.

    Aggregates outcomes from independent security controls in fixed short-circuit precedence order:
      1. Mandatory Result Presence Check
      2. Mandate Scope & Lifecycle Control
      3. Merchant Commerce Policy Control
      4. Cart Integrity Control
      5. Budget Reservation Control
      6. Replay Protection Control
      7. Nonce Validation Control
      8. Step-Up Classification Requirement
    """

    @classmethod
    def aggregate(
        cls,
        *,
        request_id: str,
        mandate_outcome: SecurityControlOutcome | MandateEvaluationResult | None,
        merchant_policy_outcome: SecurityControlOutcome | MerchantPolicyEvaluationResult | None,
        cart_integrity_outcome: SecurityControlOutcome | None,
        budget_outcome: SecurityControlOutcome | None = None,
        replay_outcome: SecurityControlOutcome | None = None,
        nonce_outcome: SecurityControlOutcome | None = None,
        step_up_outcome: SecurityControlOutcome | None = None,
        at: datetime | None = None,
    ) -> AggregatedAuthorizationResult:
        """
        Aggregate independent security control evaluations into a final authorization decision.

        Returns:
            AggregatedAuthorizationResult (ALLOW, REJECT, or STEP_UP_REQUIRED).
        """
        eval_time = at if at is not None else _utc_now()
        passed: list[str] = []
        failed: list[str] = []

        def _reject(
            reason: RejectionReason,
            detail: str,
            failed_control: str,
        ) -> AggregatedAuthorizationResult:
            failed.append(f"{failed_control}: {reason.value} — {detail}")
            return AggregatedAuthorizationResult(
                decision=PolicyDecision.REJECT,
                request_id=request_id,
                rejection_reason=reason,
                rejection_detail=detail,
                checks_passed=tuple(passed),
                checks_failed=tuple(failed),
                evaluated_at=eval_time,
            )

        # Normalize Mandate outcome
        mandate_ctrl: SecurityControlOutcome | None
        if isinstance(mandate_outcome, MandateEvaluationResult):
            mandate_ctrl = SecurityControlOutcome.from_mandate(mandate_outcome)
        else:
            mandate_ctrl = mandate_outcome

        # Normalize Merchant Policy outcome
        policy_ctrl: SecurityControlOutcome | None
        if isinstance(merchant_policy_outcome, MerchantPolicyEvaluationResult):
            policy_ctrl = SecurityControlOutcome.from_merchant_policy(merchant_policy_outcome)
        else:
            policy_ctrl = merchant_policy_outcome

        # --------------------------------------------------------------
        # Check 1: Mandatory Result Presence Check
        # --------------------------------------------------------------
        if mandate_ctrl is None:
            return _reject(
                RejectionReason.CONTROL_RESULT_MISSING,
                "Mandate evaluation control result is missing.",
                "MANDATE_SCOPE_LIFECYCLE",
            )
        if policy_ctrl is None:
            return _reject(
                RejectionReason.CONTROL_RESULT_MISSING,
                "Merchant policy evaluation control result is missing.",
                "MERCHANT_COMMERCE_POLICY",
            )
        if cart_integrity_outcome is None:
            return _reject(
                RejectionReason.CONTROL_RESULT_MISSING,
                "Cart integrity evaluation control result is missing.",
                "CART_INTEGRITY",
            )

        # --------------------------------------------------------------
        # Check 2: Mandate Scope & Lifecycle Control
        # --------------------------------------------------------------
        if not mandate_ctrl.passed or mandate_ctrl.decision is PolicyDecision.REJECT:
            reason = mandate_ctrl.rejection_reason or RejectionReason.MANDATE_NOT_ACTIVE
            detail = mandate_ctrl.detail or "Mandate scope/lifecycle check failed."
            return _reject(reason, detail, "MANDATE_SCOPE_LIFECYCLE")
        passed.append("MANDATE_SCOPE_LIFECYCLE_OK")

        # --------------------------------------------------------------
        # Check 3: Merchant Commerce Policy Control
        # --------------------------------------------------------------
        if policy_ctrl.decision is PolicyDecision.REJECT:
            reason = policy_ctrl.rejection_reason or RejectionReason.OPERATION_NOT_ALLOWED
            detail = policy_ctrl.detail or "Merchant policy check failed."
            return _reject(reason, detail, "MERCHANT_COMMERCE_POLICY")
        passed.append("MERCHANT_COMMERCE_POLICY_OK")

        # --------------------------------------------------------------
        # Check 4: Cart Integrity Control
        # --------------------------------------------------------------
        if (
            not cart_integrity_outcome.passed
            or cart_integrity_outcome.decision is PolicyDecision.REJECT
        ):
            reason = (
                cart_integrity_outcome.rejection_reason or RejectionReason.CART_INTEGRITY_VIOLATION
            )
            detail = cart_integrity_outcome.detail or "Cart integrity check failed."
            return _reject(reason, detail, "CART_INTEGRITY")
        passed.append("CART_INTEGRITY_OK")

        # --------------------------------------------------------------
        # Check 5: Budget Reservation Control (if provided)
        # --------------------------------------------------------------
        if budget_outcome is not None:
            if not budget_outcome.passed or budget_outcome.decision is PolicyDecision.REJECT:
                reason = budget_outcome.rejection_reason or RejectionReason.BUDGET_INSUFFICIENT
                detail = budget_outcome.detail or "Budget availability check failed."
                return _reject(reason, detail, "BUDGET_RESERVATION")
            passed.append("BUDGET_RESERVATION_OK")

        # --------------------------------------------------------------
        # Check 6: Replay Protection Control (if provided)
        # --------------------------------------------------------------
        if replay_outcome is not None:
            if not replay_outcome.passed or replay_outcome.decision is PolicyDecision.REJECT:
                reason = replay_outcome.rejection_reason or RejectionReason.REPLAY_ATTEMPT_DETECTED
                detail = replay_outcome.detail or "Replay protection check failed."
                return _reject(reason, detail, "REPLAY_PROTECTION")
            passed.append("REPLAY_PROTECTION_OK")

        # --------------------------------------------------------------
        # Check 7: Nonce Validation Control (if provided)
        # --------------------------------------------------------------
        if nonce_outcome is not None:
            if not nonce_outcome.passed or nonce_outcome.decision is PolicyDecision.REJECT:
                reason = nonce_outcome.rejection_reason or RejectionReason.NONCE_ALREADY_CONSUMED
                detail = nonce_outcome.detail or "Nonce validation check failed."
                return _reject(reason, detail, "NONCE_VALIDATION")
            passed.append("NONCE_VALIDATION_OK")

        # --------------------------------------------------------------
        # Check 8: Step-Up Authorization Classification Check
        # --------------------------------------------------------------
        step_up_diff: StepUpDiff | None = None
        if policy_ctrl.decision is PolicyDecision.STEP_UP_REQUIRED:
            step_up_diff = policy_ctrl.step_up_diff
        elif (
            step_up_outcome is not None
            and step_up_outcome.decision is PolicyDecision.STEP_UP_REQUIRED
        ):
            step_up_diff = step_up_outcome.step_up_diff

        if step_up_diff is not None or policy_ctrl.decision is PolicyDecision.STEP_UP_REQUIRED:
            failed.append("STEP_UP_REQUIRED")
            return AggregatedAuthorizationResult(
                decision=PolicyDecision.STEP_UP_REQUIRED,
                request_id=request_id,
                step_up_diff=step_up_diff,
                checks_passed=tuple(passed),
                checks_failed=tuple(failed),
                evaluated_at=eval_time,
            )

        passed.append("STEP_UP_NOT_REQUIRED")

        # --------------------------------------------------------------
        # Final Outcome: Unanimous Consent ALLOW
        # --------------------------------------------------------------
        return AggregatedAuthorizationResult(
            decision=PolicyDecision.ALLOW,
            request_id=request_id,
            checks_passed=tuple(passed),
            checks_failed=tuple(failed),
            evaluated_at=eval_time,
        )
