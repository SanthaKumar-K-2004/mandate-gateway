"""
S03.2 — End-to-End Commerce Orchestrator Concurrency Test Suite.

Multi-threaded concurrency tests for CommerceOrchestrator using 20 parallel workers (Section 24, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any
import unittest

from agent.orchestrator.engine import CommerceOrchestrator
from agent.orchestrator.types import OrchestratorExecutionRequest
from apps.api.contracts.mandate import MandateCreate
from apps.api.contracts.merchant import MerchantCreate, PolicyCreate
from apps.api.domain.types import Currency, McpOperation, PolicyDecision
from apps.api.routers.mandates import create_mandate
from apps.api.routers.merchants import create_merchant, update_merchant_policy


class TestOrchestratorConcurrency(unittest.TestCase):
    """Multi-threaded concurrency verification for CommerceOrchestrator."""

    def setUp(self) -> None:
        self.orchestrator = CommerceOrchestrator()
        self.merchant = create_merchant(
            MerchantCreate(name="Concurrent Store", razorpay_account_id="acc_conc_orch")
        )
        self.policy = update_merchant_policy(
            self.merchant.merchant_id,
            PolicyCreate(
                ai_commerce_enabled=True,
                currency=Currency.INR,
                allowed_categories={"electronics"},
                autonomous_purchase_limit_paise=500000,
                step_up_threshold_paise=1000000,
                max_step_up_percent=10,
                allowed_operations={McpOperation.CREATE_ORDER},
                blocked_operations={McpOperation.PAYOUT},
            ),
        )
        from datetime import datetime, timezone

        self.mandate = create_mandate(
            MandateCreate(
                buyer_id="buy_user_conc",
                merchant_scope={self.merchant.merchant_id},
                category_scope={"electronics"},
                maximum_amount_paise=1000000,
                daily_budget_paise=1000000,
                expires_at=datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            )
        )

    def test_20_parallel_orchestration_requests(self) -> None:
        """Verify 20 parallel workers executing orchestration requests maintain thread safety and determinism."""
        num_workers = 20

        def execute_worker(index: int) -> Any:
            req = OrchestratorExecutionRequest(
                user_intent_text=f"Worker {index} purchase electronic accessory",
                buyer_id="buy_user_conc",
                mandate_id=self.mandate.mandate_id,
                merchant_id=self.merchant.merchant_id,
                idempotency_key=f"idempotency_conc_worker_{index}",
            )
            return self.orchestrator.execute_intent(req)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(execute_worker, i) for i in range(num_workers)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), num_workers)
        for res in results:
            self.assertTrue(res.transaction_id.startswith("tx_e2e_"))
            self.assertIn(
                res.overall_decision, [PolicyDecision.ALLOW, PolicyDecision.STEP_UP_REQUIRED]
            )


if __name__ == "__main__":
    unittest.main()
