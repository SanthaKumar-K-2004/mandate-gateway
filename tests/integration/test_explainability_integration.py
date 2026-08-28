"""
S02.8 — Decision Trace & Explainability API Integration Tests.

Verifies GET /api/transactions/{id}/explain endpoint routing and response serialization.
"""

import unittest

from agent.explainability.engine import ExplainabilityEngine
from apps.api.contracts.explainability import ExplainabilityReportResponse
from apps.api.routers.explainability import get_transaction_explainability
from apps.api.domain.types import PolicyDecision


class TestExplainabilityIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ExplainabilityEngine()

    def test_get_transaction_explainability_endpoint(self) -> None:
        """Verify GET /api/transactions/{id}/explain handler returns valid response contract."""
        resp = get_transaction_explainability(
            transaction_id="tx_int_100",
            engine=self.engine,
        )

        self.assertIsInstance(resp, ExplainabilityReportResponse)
        self.assertEqual(resp.transaction_id, "tx_int_100")
        self.assertEqual(resp.overall_decision, PolicyDecision.ALLOW)
        self.assertIn("DECISION: AUTO_EXECUTE", resp.formatted_text_trace)
        self.assertGreater(len(resp.control_steps), 0)


if __name__ == "__main__":
    unittest.main()
