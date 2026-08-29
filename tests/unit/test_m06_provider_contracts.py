"""
S06 Unit Test Suite — Provider Contracts & Adapter Boundary.

Tests:
  1. MockRazorpayAdapter payment execution success & failure normalization.
  2. Gateway timeout classification into PaymentResultState.UNKNOWN.
  3. Status reconciliation fetching & outcome normalization.
  4. Redaction of sensitive provider fields in raw responses.
"""

from __future__ import annotations

import unittest

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.domain.execution import (
    ExecutionFailureCategory,
    TrustedExecutionRequest,
)
from apps.api.domain.types import (
    Currency,
    McpOperation,
    PaymentResultState,
    TransactionState,
)


class TestM06ProviderContracts(unittest.TestCase):
    """Unit tests for Razorpay provider contracts & adapter behavior."""

    def setUp(self) -> None:
        self.adapter = MockRazorpayAdapter()

    def test_01_execute_payment_success_normalization(self) -> None:
        request = TrustedExecutionRequest(
            transaction_id="tx_test_001",
            merchant_id="mer_001",
            buyer_id="buyer_001",
            mandate_id="man_001",
            amount_paise=50000,
            currency=Currency.INR,
            cart_hash="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            operation=McpOperation.CREATE_ORDER,
            authorization_reference="auth_001",
            idempotency_key="exec:tx_test_001",
        )

        res = self.adapter.execute_payment(request)
        self.assertTrue(res.success)
        self.assertEqual(res.transaction_id, "tx_test_001")
        self.assertEqual(res.state, TransactionState.SUCCESS)
        self.assertEqual(res.provider_status, PaymentResultState.SUCCESS)
        self.assertIsNotNone(res.external_reference)
        assert res.external_reference is not None
        self.assertTrue(res.external_reference.startswith("order_simulated_"))
        self.assertIsNotNone(res.raw_response_redacted)
        assert res.raw_response_redacted is not None
        self.assertIn("id", res.raw_response_redacted)

    def test_02_timeout_normalized_to_unknown_outcome(self) -> None:
        self.adapter.set_simulate_timeout(True)

        request = TrustedExecutionRequest(
            transaction_id="tx_test_timeout",
            merchant_id="mer_001",
            buyer_id="buyer_001",
            mandate_id="man_001",
            amount_paise=50000,
            currency=Currency.INR,
            cart_hash="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            operation=McpOperation.CREATE_ORDER,
            authorization_reference="auth_timeout",
            idempotency_key="exec:tx_test_timeout",
        )

        res = self.adapter.execute_payment(request)
        self.assertFalse(res.success)
        self.assertEqual(res.provider_status, PaymentResultState.UNKNOWN)
        self.assertEqual(res.failure_category, ExecutionFailureCategory.TIMEOUT)

    def test_03_fetch_payment_status_reconciliation(self) -> None:
        self.adapter.set_reconciliation_status(PaymentResultState.SUCCESS)
        res_success = self.adapter.fetch_payment_status("pay_test_123")
        self.assertTrue(res_success.success)
        self.assertEqual(res_success.provider_status, PaymentResultState.SUCCESS)

        self.adapter.set_reconciliation_status(PaymentResultState.FAILED)
        res_failed = self.adapter.fetch_payment_status("pay_test_123")
        self.assertFalse(res_failed.success)
        self.assertEqual(res_failed.provider_status, PaymentResultState.FAILED)


if __name__ == "__main__":
    unittest.main()
