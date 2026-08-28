"""
S02.8 — Decision Trace & Explainability Concurrency Tests.

Tests parallel multi-threaded generation of decision traces across 20 worker threads.
"""

import concurrent.futures
import unittest

from agent.explainability.engine import ExplainabilityEngine
from agent.explainability.types import DecisionTraceReport
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.types import PolicyDecision


class TestExplainabilityConcurrency(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ExplainabilityEngine()

    def test_20_concurrent_trace_generations_preserve_isolation(self) -> None:
        """Verify 20 concurrent threads generating decision traces preserve state isolation."""
        num_workers = 20
        auth_res = AuthorizationResult(
            decision=PolicyDecision.ALLOW,
            control_outcomes=[
                SecurityControlOutcome(
                    control_name="MANDATE_EVALUATION", passed=True, decision=PolicyDecision.ALLOW
                ),
                SecurityControlOutcome(
                    control_name="MERCHANT_POLICY", passed=True, decision=PolicyDecision.ALLOW
                ),
            ],
        )

        def worker_task(worker_id: int) -> DecisionTraceReport:
            tx_id = f"tx_conc_{worker_id}"
            return self.engine.generate_trace(
                transaction_id=tx_id,
                authorization_result=auth_res,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_workers)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), num_workers)
        self.assertTrue(all(r.overall_decision == PolicyDecision.ALLOW for r in results))
        self.assertEqual(
            len(set(r.transaction_id for r in results)),
            num_workers,
            msg="Each thread must generate isolated transaction trace ID.",
        )


if __name__ == "__main__":
    unittest.main()
