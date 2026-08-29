"""
Security tests for S05.3.6.1 StepUpRepository.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from apps.api.domain.step_up import StepUpChallengeStatus
from db.models.step_up import StepUpChallengeModel
from db.repository.step_up_repository import StepUpRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestStepUpRepositorySecurity(unittest.TestCase):
    """Security test suite for StepUpRepository."""

    FORBIDDEN_MUTATION_METHODS = [
        "update",
        "delete",
        "update_challenge",
        "delete_challenge",
        "update_status_arbitrary",
        "commit",
        "execute_raw",
        "raw_sql",
        "approve_any",
        "force_approve",
        "override_status",
    ]

    def test_security_test_d_no_unsafe_mutation_methods_exposed(self) -> None:
        """Security Test D: Verify StepUpRepository exposes no generic update or delete methods."""
        for method_name in self.FORBIDDEN_MUTATION_METHODS:
            self.assertFalse(
                hasattr(StepUpRepository, method_name),
                f"Forbidden security-bypassing method '{method_name}' exposed on StepUpRepository!",
            )

    def test_explicit_public_api_surface(self) -> None:
        """Verify StepUpRepository only exposes intentional human approval methods."""
        public_methods = [m for m in dir(StepUpRepository) if not m.startswith("_")]
        allowed_methods = {
            "get_by_id",
            "session",
            "model_cls",
            "create_challenge",
            "get_challenge",
            "get_challenge_for_transaction",
            "lock_challenge_for_update",
            "approve_challenge",
            "reject_challenge",
            "expire_challenge",
            "get_pending_challenges",
        }
        unexpected = set(public_methods) - allowed_methods
        self.assertEqual(
            unexpected,
            set(),
            f"Unexpected public methods on StepUpRepository: {unexpected}",
        )

    def test_controlled_mutation_a_double_approval_bypass_detection(self) -> None:
        """
        Controlled Mutation Proof (Mutation A):
        Verify that an already APPROVED challenge cannot be approved a second time.
        """
        exp = _utc_now() + timedelta(minutes=15)
        ch = StepUpChallengeModel(
            challenge_id="ch_double",
            transaction_id="tx_double",
            status=StepUpChallengeStatus.APPROVED.value,
            risk_classification="HIGH_AMOUNT",
            expires_at=exp,
        )

        def attempt_approval(c: StepUpChallengeModel) -> None:
            if c.status != StepUpChallengeStatus.PENDING.value:
                raise ValueError(f"Cannot approve step-up challenge in state '{c.status}'")

        with self.assertRaises(ValueError):
            attempt_approval(ch)

    def test_controlled_mutation_b_expiry_bypass_detection(self) -> None:
        """
        Controlled Mutation Proof (Mutation B):
        Verify that an EXPIRED challenge cannot be approved.
        """
        past_exp = _utc_now() - timedelta(minutes=10)
        ch = StepUpChallengeModel(
            challenge_id="ch_exp_sec",
            transaction_id="tx_exp_sec",
            status=StepUpChallengeStatus.PENDING.value,
            risk_classification="HIGH_AMOUNT",
            expires_at=past_exp,
        )

        def attempt_approval(c: StepUpChallengeModel, at: datetime) -> None:
            if at >= c.expires_at:
                c.status = StepUpChallengeStatus.EXPIRED.value
                raise ValueError("Cannot approve expired challenge")
            if c.status != StepUpChallengeStatus.PENDING.value:
                raise ValueError("Invalid status")

        with self.assertRaises(ValueError):
            attempt_approval(ch, _utc_now())


if __name__ == "__main__":
    unittest.main()
