"""
Unit tests for API Contracts (S01.1).
"""

import unittest
from datetime import datetime, timedelta, timezone

from apps.api.contracts.mandate import MandateCreate
from apps.api.contracts.merchant import MerchantCreate, PolicyCreate
from apps.api.contracts.transaction import CartItemProposal, PurchaseProposalRequest
from apps.api.domain.types import Currency, McpOperation


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestContracts(unittest.TestCase):
    """Test Pydantic v2 schema validation for all API contract DTOs."""

    def test_merchant_create_contract(self) -> None:
        payload = MerchantCreate(name="Alpha Shoes", razorpay_account_id="acc_test123")
        self.assertEqual(payload.name, "Alpha Shoes")

    def test_policy_create_contract(self) -> None:
        payload = PolicyCreate(
            ai_commerce_enabled=True,
            currency=Currency.INR,
            autonomous_purchase_limit_paise=500000,
            step_up_threshold_paise=300000,
        )
        self.assertTrue(payload.ai_commerce_enabled)
        self.assertIn(McpOperation.CREATE_ORDER, payload.allowed_operations)
        self.assertIn(McpOperation.PAYOUT, payload.blocked_operations)

    def test_mandate_create_contract(self) -> None:
        payload = MandateCreate(
            buyer_id="buyer-uuid-1",
            merchant_scope={"merchant-alpha"},
            maximum_amount_paise=300000,
            daily_budget_paise=500000,
            expires_at=_utc_now() + timedelta(days=1),
        )
        self.assertEqual(payload.buyer_id, "buyer-uuid-1")
        self.assertEqual(payload.currency, Currency.INR)

    def test_purchase_proposal_request_contract(self) -> None:
        item = CartItemProposal(
            product_id="prod-1",
            merchant_id="merchant-1",
            name="Shoes",
            category="footwear",
            quantity=1,
            unit_price_paise=250000,
        )
        payload = PurchaseProposalRequest(
            buyer_id="buyer-1",
            merchant_id="merchant-1",
            mandate_id="mandate-1",
            items=[item],
            total_paise=250000,
            idempotency_key="idempotency-key-xyz",
        )
        self.assertEqual(payload.total_paise, 250000)
        self.assertEqual(payload.operation, McpOperation.CREATE_ORDER)


if __name__ == "__main__":
    unittest.main()
