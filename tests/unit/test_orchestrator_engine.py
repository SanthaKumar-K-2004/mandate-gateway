"""
S03.2 — End-to-End Commerce Orchestrator Unit Test Suite.

Unit testing CommerceOrchestrator core functionality (Section 24, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

import unittest

from agent.orchestrator.engine import CommerceOrchestrator
from agent.orchestrator.types import OrchestratorExecutionRequest
from apps.api.contracts.mandate import MandateCreate
from apps.api.contracts.merchant import MerchantCreate, PolicyCreate
from apps.api.domain.types import Currency, McpOperation, PolicyDecision, TransactionState
from apps.api.routers.mandates import create_mandate
from apps.api.routers.merchants import create_merchant, update_merchant_policy


class TestOrchestratorEngineUnit(unittest.TestCase):
    """Unit test cases for CommerceOrchestrator."""

    def setUp(self) -> None:
        self.orchestrator = CommerceOrchestrator()
        self.merchant = create_merchant(
            MerchantCreate(name="Orchestrator Tech Store", razorpay_account_id="acc_orch_1")
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
                buyer_id="buy_user_orch",
                merchant_scope={self.merchant.merchant_id},
                category_scope={"electronics"},
                maximum_amount_paise=1000000,
                daily_budget_paise=1000000,
                expires_at=datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            )
        )

    def test_successful_end_to_end_intent_execution(self) -> None:
        """Verify happy path intent execution returns COMMITTED state and ALLOW decision."""
        req = OrchestratorExecutionRequest(
            user_intent_text="Buy a high quality mechanical keyboard under 2000 INR",
            buyer_id="buy_user_orch",
            mandate_id=self.mandate.mandate_id,
            merchant_id=self.merchant.merchant_id,
            idempotency_key="idempotency_key_e2e_001",
        )
        result = self.orchestrator.execute_intent(req)

        self.assertTrue(result.transaction_id.startswith("tx_e2e_"))
        self.assertEqual(result.overall_decision, PolicyDecision.ALLOW)
        self.assertEqual(result.transaction_state, TransactionState.COMMITTED)
        self.assertIsNotNone(result.receipt)
        self.assertIsNotNone(result.decision_trace_report)
        self.assertIn("DECISION:", result.formatted_text_trace or "")

    def test_step_up_required_for_large_amounts(self) -> None:
        """Verify execution requiring amount above autonomous limit transitions to STEP_UP_REQUIRED."""
        # Lower autonomous limit to 100 INR (10000 paise)
        update_merchant_policy(
            self.merchant.merchant_id,
            PolicyCreate(
                ai_commerce_enabled=True,
                currency=Currency.INR,
                allowed_categories={"electronics"},
                autonomous_purchase_limit_paise=10000,
                step_up_threshold_paise=1000000,
                max_step_up_percent=10,
                allowed_operations={McpOperation.CREATE_ORDER},
                blocked_operations={McpOperation.PAYOUT},
            ),
        )
        req = OrchestratorExecutionRequest(
            user_intent_text="Buy an expensive laptop",
            buyer_id="buy_user_orch",
            mandate_id=self.mandate.mandate_id,
            merchant_id=self.merchant.merchant_id,
            idempotency_key="idempotency_key_e2e_002",
        )
        result = self.orchestrator.execute_intent(req)

        self.assertEqual(result.overall_decision, PolicyDecision.STEP_UP_REQUIRED)
        self.assertEqual(result.transaction_state, TransactionState.STEP_UP_REQUIRED)
        self.assertIsNone(result.receipt)

    def test_merchant_ai_disabled_returns_rejection(self) -> None:
        """Verify merchant policy with AI commerce disabled returns REJECT."""
        update_merchant_policy(
            self.merchant.merchant_id,
            PolicyCreate(
                ai_commerce_enabled=False,
                currency=Currency.INR,
                allowed_categories={"electronics"},
                autonomous_purchase_limit_paise=500000,
                step_up_threshold_paise=1000000,
                max_step_up_percent=10,
                allowed_operations={McpOperation.CREATE_ORDER},
                blocked_operations={McpOperation.PAYOUT},
            ),
        )
        req = OrchestratorExecutionRequest(
            user_intent_text="Buy items",
            buyer_id="buy_user_orch",
            mandate_id=self.mandate.mandate_id,
            merchant_id=self.merchant.merchant_id,
            idempotency_key="idempotency_key_e2e_003",
        )
        result = self.orchestrator.execute_intent(req)

        self.assertEqual(result.overall_decision, PolicyDecision.REJECT)
        self.assertEqual(result.transaction_state, TransactionState.REJECTED)

    def test_idempotency_key_replay_returns_cached_result(self) -> None:
        """Verify re-executing intent with same idempotency key returns cached result."""
        req = OrchestratorExecutionRequest(
            user_intent_text="Purchase electronics item",
            buyer_id="buy_user_1",
            mandate_id=self.mandate.mandate_id,
            merchant_id=self.merchant.merchant_id,
            idempotency_key="idempotency_unit_replay_1",
        )
        res1 = self.orchestrator.execute_intent(req)
        res2 = self.orchestrator.execute_intent(req)

        self.assertIs(res1, res2)
        self.assertEqual(res1.transaction_id, res2.transaction_id)

    def test_provider_failure_returns_failure_state(self) -> None:
        """Verify payment provider failure transitions transaction to FAILURE state."""
        from apps.api.domain.execution import ExecutionFailureCategory
        from apps.api.domain.types import RejectionReason

        self.orchestrator.adapter.set_next_failure(
            category=ExecutionFailureCategory.PROVIDER_REJECTED,
            reason=RejectionReason.METHOD_NOT_AUTHORIZED,
            message="Payment declined by issuer",
        )
        req = OrchestratorExecutionRequest(
            user_intent_text="Purchase electronics item",
            buyer_id="buy_user_1",
            mandate_id=self.mandate.mandate_id,
            merchant_id=self.merchant.merchant_id,
            idempotency_key="idempotency_unit_fail_prov_1",
        )
        res = self.orchestrator.execute_intent(req)
        self.assertEqual(res.transaction_state, TransactionState.FAILURE)


if __name__ == "__main__":
    unittest.main()
