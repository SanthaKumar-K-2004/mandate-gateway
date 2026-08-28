"""
Concurrency & Linearizability test suite for S01.10 Step-Up Authorization Engine.
"""

import concurrent.futures
import unittest

from apps.api.domain.step_up import StepUpChallengeRecord, TrustedConfirmation
from apps.api.domain.step_up_engine import StepUpEngine


class TestStepUpEngineConcurrency(unittest.TestCase):
    """Exhaustive multi-threaded concurrency and race condition test suite for S01.10."""

    def setUp(self) -> None:
        self.engine = StepUpEngine()
        self.mandate_id = "mandate-conc-1000"
        self.transaction_id = "tx-conc-1000"
        self.cart_hash = "d" * 64
        self.merchant_id = "merchant-conc"
        self.approved_paise = 100000
        self.proposed_paise = 105000

    # ------------------------------------------------------------------
    # 1. 20 Concurrent Confirmation Attempts for Same Challenge
    # ------------------------------------------------------------------

    def test_20_concurrent_confirmation_attempts_allows_exactly_one(self) -> None:
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
            confirmed_by="buyer-user-conc",
        )

        def _worker() -> bool:
            try:
                self.engine.record_human_confirmation(confirmation)
                return True
            except ValueError:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(_worker) for _ in range(20)]
            results = [f.result() for f in futures]

        successful_count = sum(1 for r in results if r)
        failed_count = sum(1 for r in results if not r)

        # Exactly 1 thread must succeed, 19 fail
        self.assertEqual(successful_count, 1)
        self.assertEqual(failed_count, 19)

    # ------------------------------------------------------------------
    # 2. 50 Mixed Concurrent Requests Across 10 Unique Challenges
    # ------------------------------------------------------------------

    def test_50_mixed_concurrent_confirmations_preserves_unique_approvals(self) -> None:
        challenges = [
            self.engine.create_challenge(
                mandate_id=self.mandate_id,
                transaction_id=f"tx-mixed-{i}",
                cart_hash=self.cart_hash,
                approved_paise=self.approved_paise,
                proposed_paise=self.proposed_paise,
                merchant_id=self.merchant_id,
            )
            for i in range(10)
        ]
        pool = challenges * 5  # 50 total tasks (5 per challenge)

        def _worker(ch: StepUpChallengeRecord) -> bool:
            tc = TrustedConfirmation(
                challenge_id=ch.challenge_id,
                mandate_id=ch.mandate_id,
                transaction_id=ch.transaction_id,
                cart_hash=ch.cart_hash,
                proposed_paise=ch.proposed_paise,
                merchant_id=ch.merchant_id,
                confirmed_by="buyer-user-mixed",
            )
            try:
                self.engine.record_human_confirmation(tc)
                return True
            except ValueError:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(_worker, ch) for ch in pool]
            results = [f.result() for f in futures]

        successful_count = sum(1 for r in results if r)
        failed_count = sum(1 for r in results if not r)

        # Exactly 10 unique challenges must be approved, 40 fail
        self.assertEqual(successful_count, 10)
        self.assertEqual(failed_count, 40)


if __name__ == "__main__":
    unittest.main()
