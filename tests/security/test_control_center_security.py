"""
S03.1 — Control Center Security & Fail-Closed Test Suite.

Verifies security invariants across REST endpoints:
  - Non-existent merchant/mandate/product/transaction fail-closed (HTTP 404)
  - Invalid step-up state transition rejection (HTTP 400)
  - Secret redaction and input sanitization
"""

from __future__ import annotations

import unittest

from apps.api.contracts.merchant import MerchantCreate, PolicyCreate
from apps.api.contracts.transaction import (
    CartItemProposal,
    PurchaseProposalRequest,
    StepUpApproveRequest,
)
from apps.api.domain.types import McpOperation
from apps.api.routers.mandates import get_mandate, revoke_mandate
from apps.api.routers.merchants import (
    get_merchant,
    update_merchant_policy,
)
from apps.api.routers.products import get_product
from apps.api.routers.transactions import (
    approve_step_up,
    evaluate_purchase_proposal,
    get_transaction,
)


class TestControlCenterSecurity(unittest.TestCase):
    """Security and fail-closed test cases for S03.1 Control Center REST routers."""

    def test_empty_razorpay_account_id_raises_validation_error(self) -> None:
        """Verify empty razorpay_account_id raises ValueError/ValidationError."""
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            MerchantCreate(name="Store", razorpay_account_id="")

    def test_nonexistent_merchant_raises_404(self) -> None:
        """Verify fetching non-existent merchant raises HTTP 404."""
        with self.assertRaises(Exception) as ctx:
            get_merchant("mer_nonexistent_999")
        self.assertEqual(getattr(ctx.exception, "status_code", None), 404)

    def test_nonexistent_merchant_policy_update_raises_404(self) -> None:
        """Verify updating policy for non-existent merchant raises HTTP 404."""
        payload = PolicyCreate(
            ai_commerce_enabled=True,
            autonomous_purchase_limit_paise=100000,
            step_up_threshold_paise=200000,
            allowed_operations={McpOperation.CREATE_ORDER},
            blocked_operations={McpOperation.PAYOUT},
        )
        with self.assertRaises(Exception) as ctx:
            update_merchant_policy("mer_nonexistent_999", payload)
        self.assertEqual(getattr(ctx.exception, "status_code", None), 404)

    def test_nonexistent_product_raises_404(self) -> None:
        """Verify fetching non-existent product raises HTTP 404."""
        with self.assertRaises(Exception) as ctx:
            get_product("prd_nonexistent_999")
        self.assertEqual(getattr(ctx.exception, "status_code", None), 404)

    def test_nonexistent_mandate_raises_404(self) -> None:
        """Verify fetching or revoking non-existent mandate raises HTTP 404."""
        with self.assertRaises(Exception) as ctx:
            get_mandate("man_nonexistent_999")
        self.assertEqual(getattr(ctx.exception, "status_code", None), 404)

        with self.assertRaises(Exception) as ctx:
            revoke_mandate("man_nonexistent_999")
        self.assertEqual(getattr(ctx.exception, "status_code", None), 404)

    def test_nonexistent_transaction_raises_404(self) -> None:
        """Verify fetching non-existent transaction raises HTTP 404."""
        with self.assertRaises(Exception) as ctx:
            get_transaction("tx_nonexistent_999")
        self.assertEqual(getattr(ctx.exception, "status_code", None), 404)

    def test_invalid_step_up_state_transition_raises_400(self) -> None:
        """Verify attempting to approve step-up on transaction not in STEP_UP_REQUIRED raises HTTP 400."""

        tx = evaluate_purchase_proposal(
            PurchaseProposalRequest(
                buyer_id="buy_user_low",
                merchant_id="mer_shop_1",
                mandate_id="man_buyer_1",
                operation=McpOperation.CREATE_ORDER,
                items=[
                    CartItemProposal(
                        product_id="prd_1",
                        merchant_id="mer_shop_1",
                        name="Mouse",
                        category="electronics",
                        quantity=1,
                        unit_price_paise=100000,
                    )
                ],
                total_paise=100000,
                idempotency_key="idemp_sec_001",
            )
        )

        with self.assertRaises(Exception) as ctx:
            approve_step_up(
                tx.transaction_id,
                StepUpApproveRequest(
                    buyer_id="buy_user_low",
                    transaction_id=tx.transaction_id,
                    approved_amount_paise=100000,
                ),
            )
        self.assertEqual(getattr(ctx.exception, "status_code", None), 400)


if __name__ == "__main__":
    unittest.main()
