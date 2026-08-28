"""
Unit, Security, Adversarial, Precedence & Failure tests for S01.5 Authorization Aggregation Engine.
"""

import concurrent.futures
import unittest
from datetime import datetime, timedelta, timezone

from apps.api.contracts.transaction import StepUpDiff
from apps.api.domain.authorization_aggregator import (
    AuthorizationAggregator,
    SecurityControlOutcome,
)
from apps.api.domain.intent import CommerceIntent
from apps.api.domain.mandate import BuyerMandate
from apps.api.domain.mandate_lifecycle import MandateEvaluator
from apps.api.domain.merchant import MerchantPolicy
from apps.api.domain.merchant_policy_engine import MerchantPolicyEngine
from apps.api.domain.types import (
    Currency,
    MandateStatus,
    PolicyDecision,
    Region,
    RejectionReason,
)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestAuthorizationAggregator(unittest.TestCase):
    """Exhaustive test suite for S01.5 Authorization Aggregation Engine."""

    def setUp(self) -> None:
        self.request_id = "req-test-999"

        # Baseline PASS security control outcomes
        self.mandate_pass = SecurityControlOutcome(
            control_name="MANDATE_SCOPE_LIFECYCLE",
            passed=True,
            decision=PolicyDecision.ALLOW,
        )
        self.policy_pass = SecurityControlOutcome(
            control_name="MERCHANT_COMMERCE_POLICY",
            passed=True,
            decision=PolicyDecision.ALLOW,
        )
        self.cart_pass = SecurityControlOutcome(
            control_name="CART_INTEGRITY",
            passed=True,
            decision=PolicyDecision.ALLOW,
        )
        self.budget_pass = SecurityControlOutcome(
            control_name="BUDGET_RESERVATION",
            passed=True,
            decision=PolicyDecision.ALLOW,
        )
        self.replay_pass = SecurityControlOutcome(
            control_name="REPLAY_PROTECTION",
            passed=True,
            decision=PolicyDecision.ALLOW,
        )
        self.nonce_pass = SecurityControlOutcome(
            control_name="NONCE_VALIDATION",
            passed=True,
            decision=PolicyDecision.ALLOW,
        )

    # ------------------------------------------------------------------
    # 1. Unanimous Consent Rule (ALLOW + ALLOW + ALLOW -> ALLOW)
    # ------------------------------------------------------------------

    def test_unanimous_consent_returns_allow(self) -> None:
        res = AuthorizationAggregator.aggregate(
            request_id=self.request_id,
            mandate_outcome=self.mandate_pass,
            merchant_policy_outcome=self.policy_pass,
            cart_integrity_outcome=self.cart_pass,
            budget_outcome=self.budget_pass,
            replay_outcome=self.replay_pass,
            nonce_outcome=self.nonce_pass,
        )
        self.assertTrue(res.is_allowed)
        self.assertEqual(res.decision, PolicyDecision.ALLOW)
        self.assertIsNone(res.rejection_reason)
        self.assertIn("MANDATE_SCOPE_LIFECYCLE_OK", res.checks_passed)
        self.assertIn("MERCHANT_COMMERCE_POLICY_OK", res.checks_passed)
        self.assertIn("CART_INTEGRITY_OK", res.checks_passed)
        self.assertIn("BUDGET_RESERVATION_OK", res.checks_passed)

    # ------------------------------------------------------------------
    # 2. Short-Circuit Precedence & Individual Control Failure Modes
    # ------------------------------------------------------------------

    def test_mandate_reject_short_circuits_to_reject(self) -> None:
        mandate_fail = SecurityControlOutcome(
            control_name="MANDATE_SCOPE_LIFECYCLE",
            passed=False,
            decision=PolicyDecision.REJECT,
            rejection_reason=RejectionReason.MANDATE_EXPIRED,
            detail="Mandate has expired.",
        )
        res = AuthorizationAggregator.aggregate(
            request_id=self.request_id,
            mandate_outcome=mandate_fail,
            merchant_policy_outcome=self.policy_pass,
            cart_integrity_outcome=self.cart_pass,
        )
        self.assertTrue(res.is_rejected)
        self.assertEqual(res.rejection_reason, RejectionReason.MANDATE_EXPIRED)

    def test_merchant_policy_reject_short_circuits_to_reject(self) -> None:
        policy_fail = SecurityControlOutcome(
            control_name="MERCHANT_COMMERCE_POLICY",
            passed=False,
            decision=PolicyDecision.REJECT,
            rejection_reason=RejectionReason.AI_COMMERCE_DISABLED,
            detail="AI Commerce disabled by merchant.",
        )
        res = AuthorizationAggregator.aggregate(
            request_id=self.request_id,
            mandate_outcome=self.mandate_pass,
            merchant_policy_outcome=policy_fail,
            cart_integrity_outcome=self.cart_pass,
        )
        self.assertTrue(res.is_rejected)
        self.assertEqual(res.rejection_reason, RejectionReason.AI_COMMERCE_DISABLED)

    def test_cart_integrity_reject_short_circuits_to_reject(self) -> None:
        cart_fail = SecurityControlOutcome(
            control_name="CART_INTEGRITY",
            passed=False,
            decision=PolicyDecision.REJECT,
            rejection_reason=RejectionReason.CART_INTEGRITY_VIOLATION,
            detail="Cart hash mismatch.",
        )
        res = AuthorizationAggregator.aggregate(
            request_id=self.request_id,
            mandate_outcome=self.mandate_pass,
            merchant_policy_outcome=self.policy_pass,
            cart_integrity_outcome=cart_fail,
        )
        self.assertTrue(res.is_rejected)
        self.assertEqual(res.rejection_reason, RejectionReason.CART_INTEGRITY_VIOLATION)

    def test_budget_reject_short_circuits_to_reject(self) -> None:
        budget_fail = SecurityControlOutcome(
            control_name="BUDGET_RESERVATION",
            passed=False,
            decision=PolicyDecision.REJECT,
            rejection_reason=RejectionReason.BUDGET_INSUFFICIENT,
            detail="Daily budget limit exceeded.",
        )
        res = AuthorizationAggregator.aggregate(
            request_id=self.request_id,
            mandate_outcome=self.mandate_pass,
            merchant_policy_outcome=self.policy_pass,
            cart_integrity_outcome=self.cart_pass,
            budget_outcome=budget_fail,
        )
        self.assertTrue(res.is_rejected)
        self.assertEqual(res.rejection_reason, RejectionReason.BUDGET_INSUFFICIENT)

    def test_replay_reject_short_circuits_to_reject(self) -> None:
        replay_fail = SecurityControlOutcome(
            control_name="REPLAY_PROTECTION",
            passed=False,
            decision=PolicyDecision.REJECT,
            rejection_reason=RejectionReason.REPLAY_ATTEMPT_DETECTED,
            detail="Idempotency key already used.",
        )
        res = AuthorizationAggregator.aggregate(
            request_id=self.request_id,
            mandate_outcome=self.mandate_pass,
            merchant_policy_outcome=self.policy_pass,
            cart_integrity_outcome=self.cart_pass,
            replay_outcome=replay_fail,
        )
        self.assertTrue(res.is_rejected)
        self.assertEqual(res.rejection_reason, RejectionReason.REPLAY_ATTEMPT_DETECTED)

    # ------------------------------------------------------------------
    # 3. Missing Control Result Fails Closed (REJECT)
    # ------------------------------------------------------------------

    def test_missing_mandate_control_result_rejected(self) -> None:
        res = AuthorizationAggregator.aggregate(
            request_id=self.request_id,
            mandate_outcome=None,  # Missing!
            merchant_policy_outcome=self.policy_pass,
            cart_integrity_outcome=self.cart_pass,
        )
        self.assertTrue(res.is_rejected)
        self.assertEqual(res.rejection_reason, RejectionReason.CONTROL_RESULT_MISSING)

    def test_missing_merchant_policy_control_result_rejected(self) -> None:
        res = AuthorizationAggregator.aggregate(
            request_id=self.request_id,
            mandate_outcome=self.mandate_pass,
            merchant_policy_outcome=None,  # Missing!
            cart_integrity_outcome=self.cart_pass,
        )
        self.assertTrue(res.is_rejected)
        self.assertEqual(res.rejection_reason, RejectionReason.CONTROL_RESULT_MISSING)

    def test_missing_cart_integrity_control_result_rejected(self) -> None:
        res = AuthorizationAggregator.aggregate(
            request_id=self.request_id,
            mandate_outcome=self.mandate_pass,
            merchant_policy_outcome=self.policy_pass,
            cart_integrity_outcome=None,  # Missing!
        )
        self.assertTrue(res.is_rejected)
        self.assertEqual(res.rejection_reason, RejectionReason.CONTROL_RESULT_MISSING)

    # ------------------------------------------------------------------
    # 4. Step-Up Required Handling
    # ------------------------------------------------------------------

    def test_step_up_required_outcome(self) -> None:
        step_up_diff = StepUpDiff(
            approved_paise=500000,
            proposed_paise=530000,
            delta_paise=30000,
            delta_percent=6.0,
            reason="Within +10% step-up tolerance window.",
        )
        step_up_policy = SecurityControlOutcome(
            control_name="MERCHANT_COMMERCE_POLICY",
            passed=True,
            decision=PolicyDecision.STEP_UP_REQUIRED,
            step_up_diff=step_up_diff,
        )

        res = AuthorizationAggregator.aggregate(
            request_id=self.request_id,
            mandate_outcome=self.mandate_pass,
            merchant_policy_outcome=step_up_policy,
            cart_integrity_outcome=self.cart_pass,
        )
        self.assertTrue(res.is_step_up_required)
        self.assertEqual(res.decision, PolicyDecision.STEP_UP_REQUIRED)
        self.assertIsNotNone(res.step_up_diff)
        self.assertEqual(res.step_up_diff.delta_paise, 30000)  # type: ignore

    # ------------------------------------------------------------------
    # 5. Integration with S01.4 MandateEvaluator & S01.3 Policy Engine Results
    # ------------------------------------------------------------------

    def test_domain_result_objects_aggregation(self) -> None:
        buyer_id = "buyer-10"
        merchant_id = "merchant-10"

        mandate = BuyerMandate(
            mandate_id="mandate-10",
            buyer_id=buyer_id,
            merchant_scope=frozenset({merchant_id}),
            maximum_amount_paise=500000,
            daily_budget_paise=1000000,
            currency=Currency.INR,
            autonomous_execution=True,
            expires_at=_utc_now() + timedelta(days=1),
            status=MandateStatus.ACTIVE,
        )
        intent = CommerceIntent(
            intent_id="intent-test-agg",
            buyer_id=buyer_id,
            target_merchant_id=merchant_id,
            raw_prompt="Buy items",
            max_budget_paise=300000,
            currency=Currency.INR,
            region=Region.IN,
            metadata={"operation": "create_order"},
        )
        mandate_res = MandateEvaluator.evaluate(
            mandate=mandate,
            intent=intent,
        )

        merchant_policy = MerchantPolicy(
            merchant_id=merchant_id,
            policy_version=1,
            ai_commerce_enabled=True,
            currency=Currency.INR,
            autonomous_purchase_limit_paise=1000000,
            step_up_threshold_paise=500000,
            max_step_up_percent=10,
            expires_at=_utc_now() + timedelta(days=1),
        )
        policy_res = MerchantPolicyEngine.evaluate(
            policy=merchant_policy,
            intent=intent,
        )

        res = AuthorizationAggregator.aggregate(
            request_id=self.request_id,
            mandate_outcome=mandate_res,
            merchant_policy_outcome=policy_res,
            cart_integrity_outcome=self.cart_pass,
        )
        self.assertTrue(res.is_allowed)

    # ------------------------------------------------------------------
    # 6. Concurrency Safety
    # ------------------------------------------------------------------

    def test_concurrent_authorization_aggregations(self) -> None:
        def _eval_agg(i: int) -> bool:
            req_id = f"req-concurrent-{i}"
            res = AuthorizationAggregator.aggregate(
                request_id=req_id,
                mandate_outcome=self.mandate_pass,
                merchant_policy_outcome=self.policy_pass,
                cart_integrity_outcome=self.cart_pass,
                budget_outcome=self.budget_pass,
                replay_outcome=self.replay_pass,
                nonce_outcome=self.nonce_pass,
            )
            return res.is_allowed

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_eval_agg, i) for i in range(20)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 20)
        self.assertTrue(all(results))


if __name__ == "__main__":
    unittest.main()
