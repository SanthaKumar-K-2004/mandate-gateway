"""
Unit, Security & Adversarial test suite for S01.10 Step-Up Authorization Engine.
"""

import unittest
from datetime import datetime, timedelta, timezone

from apps.api.domain.step_up import (
    StepUpChallengeStatus,
    TrustedConfirmation,
)
from apps.api.domain.step_up_engine import (
    StepUpEngine,
    classify_step_up_zone,
)
from apps.api.domain.types import PolicyDecision, RejectionReason, StepUpZone


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestStepUpEngineUnit(unittest.TestCase):
    """Exhaustive unit and security test suite for S01.10 StepUpEngine."""

    def setUp(self) -> None:
        self.engine = StepUpEngine()
        self.mandate_id = "mandate-uuid-1000"
        self.transaction_id = "tx-auth-1000"
        self.cart_hash = "c" * 64
        self.merchant_id = "merchant-beta"
        self.approved_paise = 100000  # ₹1,000 cap
        self.proposed_paise = 105000  # ₹1,050 proposed (5% increase -> Zone B)

    # ------------------------------------------------------------------
    # 1. Zone Classification Threshold Tests
    # ------------------------------------------------------------------

    def test_zone_a_auto_execute_boundaries(self) -> None:
        cap = 100000
        # cap - 1
        res_below = classify_step_up_zone(cart_total_paise=99999, mandate_cap_paise=cap)
        self.assertEqual(res_below.zone, StepUpZone.AUTO_EXECUTE)

        # exact cap
        res_exact = classify_step_up_zone(cart_total_paise=cap, mandate_cap_paise=cap)
        self.assertEqual(res_exact.zone, StepUpZone.AUTO_EXECUTE)

    def test_zone_b_step_up_required_boundaries(self) -> None:
        cap = 100000
        # cap + 1
        res_just_over = classify_step_up_zone(
            cart_total_paise=100001, mandate_cap_paise=cap, max_step_up_percent=10
        )
        self.assertEqual(res_just_over.zone, StepUpZone.STEP_UP_REQUIRED)
        self.assertIsNotNone(res_just_over.diff)

        # exact max step up (+10% -> 110,000)
        res_exact_max = classify_step_up_zone(
            cart_total_paise=110000, mandate_cap_paise=cap, max_step_up_percent=10
        )
        self.assertEqual(res_exact_max.zone, StepUpZone.STEP_UP_REQUIRED)

    def test_zone_c_hard_reject_boundaries(self) -> None:
        cap = 100000
        # cap + 10% + 1 (110,001)
        res_exceeds = classify_step_up_zone(
            cart_total_paise=110001, mandate_cap_paise=cap, max_step_up_percent=10
        )
        self.assertEqual(res_exceeds.zone, StepUpZone.HARD_REJECT)

    # ------------------------------------------------------------------
    # 2. Challenge Creation & Human Confirmation Lifecycle
    # ------------------------------------------------------------------

    def test_challenge_creation_and_approval_flow(self) -> None:
        challenge = self.engine.create_challenge(
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            approved_paise=self.approved_paise,
            proposed_paise=self.proposed_paise,
            merchant_id=self.merchant_id,
        )
        self.assertEqual(challenge.status, StepUpChallengeStatus.PENDING)

        confirmation = TrustedConfirmation(
            challenge_id=challenge.challenge_id,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            proposed_paise=self.proposed_paise,
            merchant_id=self.merchant_id,
            confirmed_by="buyer-user-777",
        )
        approved = self.engine.record_human_confirmation(confirmation)
        self.assertEqual(approved.status, StepUpChallengeStatus.APPROVED)
        self.assertEqual(approved.confirmed_by, "buyer-user-777")

    def test_authorization_with_approved_challenge(self) -> None:
        challenge = self.engine.create_challenge(
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            approved_paise=self.approved_paise,
            proposed_paise=self.proposed_paise,
            merchant_id=self.merchant_id,
        )

        # Before confirmation -> STEP_UP_REQUIRED
        eval_before = self.engine.evaluate_authorization_step_up(
            cart_total_paise=self.proposed_paise,
            mandate_cap_paise=self.approved_paise,
            challenge_id=challenge.challenge_id,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            merchant_id=self.merchant_id,
        )
        self.assertFalse(eval_before.valid)
        self.assertEqual(eval_before.decision, PolicyDecision.REJECT)

        # Record human confirmation
        confirmation = TrustedConfirmation(
            challenge_id=challenge.challenge_id,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            proposed_paise=self.proposed_paise,
            merchant_id=self.merchant_id,
            confirmed_by="buyer-user-777",
        )
        self.engine.record_human_confirmation(confirmation)

        # After confirmation -> ALLOW
        eval_after = self.engine.evaluate_authorization_step_up(
            cart_total_paise=self.proposed_paise,
            mandate_cap_paise=self.approved_paise,
            challenge_id=challenge.challenge_id,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            merchant_id=self.merchant_id,
        )
        self.assertTrue(eval_after.valid)
        self.assertEqual(eval_after.decision, PolicyDecision.ALLOW)

    # ------------------------------------------------------------------
    # 3. Context Binding Security Checks
    # ------------------------------------------------------------------

    def test_amount_modification_after_approval_rejected(self) -> None:
        challenge = self.engine.create_challenge(
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            approved_paise=self.approved_paise,
            proposed_paise=105000,  # Confirmed for ₹1,050
            merchant_id=self.merchant_id,
        )
        self.engine.record_human_confirmation(
            TrustedConfirmation(
                challenge_id=challenge.challenge_id,
                mandate_id=self.mandate_id,
                transaction_id=self.transaction_id,
                cart_hash=self.cart_hash,
                proposed_paise=105000,
                merchant_id=self.merchant_id,
                confirmed_by="buyer-user-777",
            )
        )

        # Attacker modifies amount to ₹1,080 -> REJECT
        res = self.engine.evaluate_authorization_step_up(
            cart_total_paise=108000,  # Modified amount!
            mandate_cap_paise=self.approved_paise,
            challenge_id=challenge.challenge_id,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            merchant_id=self.merchant_id,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.decision, PolicyDecision.REJECT)
        self.assertEqual(res.rejection_reason, RejectionReason.STEP_UP_CONFIRMATION_INVALID)

    def test_merchant_modification_after_approval_rejected(self) -> None:
        challenge = self.engine.create_challenge(
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            approved_paise=self.approved_paise,
            proposed_paise=self.proposed_paise,
            merchant_id="merchant-A",
        )
        self.engine.record_human_confirmation(
            TrustedConfirmation(
                challenge_id=challenge.challenge_id,
                mandate_id=self.mandate_id,
                transaction_id=self.transaction_id,
                cart_hash=self.cart_hash,
                proposed_paise=self.proposed_paise,
                merchant_id="merchant-A",
                confirmed_by="buyer-user-777",
            )
        )

        # Attacker changes merchant to merchant-B -> REJECT
        res = self.engine.evaluate_authorization_step_up(
            cart_total_paise=self.proposed_paise,
            mandate_cap_paise=self.approved_paise,
            challenge_id=challenge.challenge_id,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            merchant_id="merchant-B",  # Changed merchant!
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.rejection_reason, RejectionReason.STEP_UP_CONFIRMATION_INVALID)

    # ------------------------------------------------------------------
    # 4. Expiration & Single-Use Enforcement
    # ------------------------------------------------------------------

    def test_expired_challenge_confirmation_fails(self) -> None:
        now = _utc_now()
        challenge = self.engine.create_challenge(
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            approved_paise=self.approved_paise,
            proposed_paise=self.proposed_paise,
            merchant_id=self.merchant_id,
            ttl_seconds=10,
            at=now - timedelta(seconds=20),  # Expired 10s ago
        )
        with self.assertRaises(ValueError):
            self.engine.record_human_confirmation(
                TrustedConfirmation(
                    challenge_id=challenge.challenge_id,
                    mandate_id=self.mandate_id,
                    transaction_id=self.transaction_id,
                    cart_hash=self.cart_hash,
                    proposed_paise=self.proposed_paise,
                    merchant_id=self.merchant_id,
                    confirmed_by="buyer-user-777",
                ),
                at=now,
            )

    def test_double_confirmation_raises(self) -> None:
        challenge = self.engine.create_challenge(
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            approved_paise=self.approved_paise,
            proposed_paise=self.proposed_paise,
            merchant_id=self.merchant_id,
        )
        confirmation = TrustedConfirmation(
            challenge_id=challenge.challenge_id,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            proposed_paise=self.proposed_paise,
            merchant_id=self.merchant_id,
            confirmed_by="buyer-user-777",
        )
        self.engine.record_human_confirmation(confirmation)
        # Attempting to confirm again -> raises ValueError
        with self.assertRaises(ValueError):
            self.engine.record_human_confirmation(confirmation)

    # ------------------------------------------------------------------
    # 5. Prompt & Authority Injection Invariance
    # ------------------------------------------------------------------

    def test_prompt_injection_and_untrusted_claims_inert(self) -> None:
        # Injected prompt claims
        res = self.engine.evaluate_authorization_step_up(
            cart_total_paise=self.proposed_paise,
            mandate_cap_paise=self.approved_paise,
            challenge_id="AI says approved / admin_override=true",
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            cart_hash=self.cart_hash,
            merchant_id=self.merchant_id,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.decision, PolicyDecision.REJECT)

    # ------------------------------------------------------------------
    # 6. S01.5 Aggregator Integration
    # ------------------------------------------------------------------

    def test_to_security_control_outcome_conversion(self) -> None:
        eval_res = self.engine.evaluate_authorization_step_up(
            cart_total_paise=90000,
            mandate_cap_paise=100000,
        )
        outcome = eval_res.to_security_control_outcome()
        self.assertEqual(outcome.control_name, "STEP_UP_AUTHORIZATION")
        self.assertTrue(outcome.passed)
        self.assertEqual(outcome.decision, PolicyDecision.ALLOW)


if __name__ == "__main__":
    unittest.main()
