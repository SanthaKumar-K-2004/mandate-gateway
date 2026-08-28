"""
S02.4 — Agent Step-Up Concurrency & Race Condition Tests.
"""

from concurrent.futures import ThreadPoolExecutor
import unittest

from agent.stepup.manager import AgentStepUpManager
from agent.stepup.types import AgentStepUpDecision, HumanDecisionChoice, StepUpStatus


class TestStepUpConcurrency(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = AgentStepUpManager()

    def test_parallel_challenge_creation_and_resolution(self) -> None:
        """Verify 20 concurrent threads can safely create and resolve step-up challenges."""
        worker_count = 20

        def run_worker(idx: int) -> StepUpStatus:
            sess_id = f"sess_conc_{idx}"
            ch = self.manager.create_challenge(
                session_id=sess_id,
                buyer_id=f"buyer_{idx}",
                merchant_id="merchant_conc_01",
                mandate_id=f"mandate_{idx}",
                cart_hash=f"HASH_{idx}",
                total_paise=500000 + idx * 100,
            )

            decision = AgentStepUpDecision(
                challenge_id=ch.challenge_id,
                approver_id=f"user_human_{idx}",
                decision=(
                    HumanDecisionChoice.APPROVE if idx % 2 == 0 else HumanDecisionChoice.REJECT
                ),
            )

            resolved = self.manager.resolve_decision(
                decision=decision,
                session_id=sess_id,
                buyer_id=f"buyer_{idx}",
                merchant_id="merchant_conc_01",
                current_cart_hash=f"HASH_{idx}",
                current_total_paise=500000 + idx * 100,
                agent_id=f"agent_conc_{idx}",
            )
            return resolved.status

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            results = list(executor.map(run_worker, range(worker_count)))

        self.assertEqual(len(results), worker_count)
        for idx, status in enumerate(results):
            expected = StepUpStatus.APPROVED if idx % 2 == 0 else StepUpStatus.REJECTED
            self.assertEqual(status, expected)


if __name__ == "__main__":
    unittest.main()
