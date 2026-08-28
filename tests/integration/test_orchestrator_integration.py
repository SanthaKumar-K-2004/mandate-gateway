"""
S03.2 — End-to-End Commerce Orchestrator Integration Test Suite.

End-to-End integration tests for CommerceOrchestrator and REST endpoint (Section 24 & Section 28, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

import unittest

from agent.orchestrator.types import OrchestratorExecutionRequest
from apps.api.contracts.mandate import MandateCreate
from apps.api.contracts.merchant import MerchantCreate, PolicyCreate
from apps.api.domain.types import Currency, McpOperation, PolicyDecision, TransactionState
from apps.api.routers.mandates import create_mandate
from apps.api.routers.merchants import create_merchant, update_merchant_policy
from apps.api.routers.orchestrator import execute_end_to_end_intent


class TestOrchestratorIntegration(unittest.TestCase):
    """Integration verification test cases for end-to-end commerce orchestration."""

    def setUp(self) -> None:
        self.merchant = create_merchant(
            MerchantCreate(name="Integration Hypermarket", razorpay_account_id="acc_int_orch")
        )
        self.policy = update_merchant_policy(
            self.merchant.merchant_id,
            PolicyCreate(
                ai_commerce_enabled=True,
                currency=Currency.INR,
                allowed_categories={"electronics", "books"},
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
                buyer_id="buy_user_int",
                merchant_scope={self.merchant.merchant_id},
                category_scope={"electronics"},
                maximum_amount_paise=500000,
                daily_budget_paise=500000,
                expires_at=datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            )
        )

    def test_full_rest_router_end_to_end_execution(self) -> None:
        """Verify executing intent via REST router produces valid transaction, receipt, and trace report."""
        req = OrchestratorExecutionRequest(
            user_intent_text="Order wireless bluetooth earbuds for work under 1500 INR",
            buyer_id="buy_user_int",
            mandate_id=self.mandate.mandate_id,
            merchant_id=self.merchant.merchant_id,
            idempotency_key="idempotency_key_rest_e2e_001",
        )
        res = execute_end_to_end_intent(req)

        self.assertIsNotNone(res.transaction_id)
        self.assertEqual(res.overall_decision, PolicyDecision.ALLOW)
        self.assertEqual(res.transaction_state, TransactionState.COMMITTED)
        self.assertEqual(res.buyer_id, "buy_user_int")
        self.assertEqual(res.merchant_id, self.merchant.merchant_id)
        self.assertEqual(res.mandate_id, self.mandate.mandate_id)
        self.assertGreater(res.amount_paise, 0)
        self.assertIsNotNone(res.receipt)
        self.assertTrue(res.receipt.signature.startswith("ed25519:"))
        self.assertIsNotNone(res.decision_trace_report)
        self.assertEqual(res.decision_trace_report.transaction_id, res.transaction_id)


if __name__ == "__main__":
    unittest.main()
