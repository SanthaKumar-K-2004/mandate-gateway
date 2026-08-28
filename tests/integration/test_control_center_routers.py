"""
S03.1 — Control Center REST Routers Integration Test Suite.

Verifies end-to-end functionality of all Section 28 REST endpoints:
  - Merchants & Merchant Policies
  - Products & Catalog
  - Buyer Mandates
  - Purchase Proposals & Transactions
  - Audit Trail & Action Receipts
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from apps.api.contracts.mandate import MandateCreate
from apps.api.contracts.merchant import MerchantCreate, PolicyCreate
from apps.api.contracts.product import ProductCreateRequest
from apps.api.contracts.transaction import (
    CartItemProposal,
    PurchaseProposalRequest,
    StepUpApproveRequest,
    StepUpRejectRequest,
)
from apps.api.domain.types import Currency, MandateStatus, McpOperation, TransactionState
from apps.api.routers.audit import (
    get_receipt,
    get_transaction_events,
    verify_receipt_endpoint,
)
from apps.api.routers.mandates import (
    create_mandate,
    get_mandate,
    revoke_mandate,
)
from apps.api.routers.merchants import (
    create_merchant,
    get_merchant,
    get_merchant_policy,
    update_merchant_policy,
)
from apps.api.routers.products import (
    create_product,
    get_product,
    list_merchant_products,
)
from apps.api.routers.transactions import (
    approve_step_up,
    evaluate_purchase_proposal,
    reject_step_up,
)


class TestControlCenterRoutersIntegration(unittest.TestCase):
    """Integration test cases for S03.1 Control Center REST routers."""

    def test_merchant_and_policy_lifecycle(self) -> None:
        """Verify merchant registration and policy creation/retrieval."""
        merchant_payload = MerchantCreate(
            name="Apex Tech Store",
            razorpay_account_id="acc_apex123",
        )
        merchant = create_merchant(merchant_payload)
        self.assertTrue(merchant.merchant_id.startswith("mer_"))
        self.assertEqual(merchant.name, "Apex Tech Store")

        # Fetch merchant
        fetched = get_merchant(merchant.merchant_id)
        self.assertEqual(fetched.merchant_id, merchant.merchant_id)

        # Update merchant policy
        policy_payload = PolicyCreate(
            ai_commerce_enabled=True,
            currency=Currency.INR,
            allowed_categories={"electronics", "books"},
            autonomous_purchase_limit_paise=300000,
            step_up_threshold_paise=800000,
            max_step_up_percent=10,
            allowed_operations={McpOperation.CREATE_ORDER},
            blocked_operations={McpOperation.PAYOUT},
        )
        updated_policy = update_merchant_policy(merchant.merchant_id, policy_payload)
        self.assertEqual(updated_policy.merchant_id, merchant.merchant_id)
        self.assertEqual(updated_policy.policy_version, 2)
        self.assertEqual(updated_policy.autonomous_purchase_limit_paise, 300000)

        # Fetch policy
        fetched_policy = get_merchant_policy(merchant.merchant_id)
        self.assertEqual(fetched_policy.policy_version, 2)

    def test_catalog_product_lifecycle(self) -> None:
        """Verify catalog product registration and listing."""
        merchant = create_merchant(
            MerchantCreate(name="Gadget Zone", razorpay_account_id="acc_gz1")
        )

        product_payload = ProductCreateRequest(
            name="Mechanical Keyboard",
            category="electronics",
            price_paise=250000,
            currency=Currency.INR,
            description="RGB Mechanical Keyboard",
            stock_quantity=50,
        )
        product = create_product(merchant.merchant_id, product_payload)
        self.assertTrue(product.product_id.startswith("prd_"))
        self.assertEqual(product.name, "Mechanical Keyboard")

        # Fetch product
        fetched = get_product(product.product_id)
        self.assertEqual(fetched.product_id, product.product_id)

        # List merchant products
        plist = list_merchant_products(merchant.merchant_id)
        self.assertEqual(plist.total_count, 1)
        self.assertEqual(plist.products[0].product_id, product.product_id)

    def test_buyer_mandate_lifecycle(self) -> None:
        """Verify buyer mandate creation, fetching, and revocation."""
        mandate_payload = MandateCreate(
            buyer_id="buy_test_user_01",
            merchant_scope={"mer_test_01"},
            category_scope={"electronics"},
            maximum_amount_paise=500000,
            daily_budget_paise=1000000,
            currency=Currency.INR,
            autonomous_execution=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        mandate = create_mandate(mandate_payload)
        self.assertTrue(mandate.mandate_id.startswith("man_"))
        self.assertEqual(mandate.status, MandateStatus.ACTIVE)

        # Fetch mandate
        fetched = get_mandate(mandate.mandate_id)
        self.assertEqual(fetched.mandate_id, mandate.mandate_id)

        # Revoke mandate
        revoked = revoke_mandate(mandate.mandate_id)
        self.assertEqual(revoked.status, MandateStatus.REVOKED)

        # Verify revoked status in get_mandate
        refetched = get_mandate(mandate.mandate_id)
        self.assertEqual(refetched.status, MandateStatus.REVOKED)

    def test_purchase_proposal_and_step_up_flow(self) -> None:
        """Verify proposal evaluation, step-up requirement, and human approval/rejection."""
        # 1. Proposal under limit -> AUTHORIZED
        low_proposal = PurchaseProposalRequest(
            buyer_id="buy_user_low",
            merchant_id="mer_shop_1",
            mandate_id="man_buyer_1",
            operation=McpOperation.CREATE_ORDER,
            items=[
                CartItemProposal(
                    product_id="prd_1",
                    merchant_id="mer_shop_1",
                    name="Wireless Mouse",
                    category="electronics",
                    quantity=1,
                    unit_price_paise=150000,
                )
            ],
            total_paise=150000,
            currency=Currency.INR,
            idempotency_key="idemp_low_001",
        )
        tx_low = evaluate_purchase_proposal(low_proposal)
        self.assertEqual(tx_low.state, TransactionState.AUTHORIZED)

        # 2. Proposal over limit -> STEP_UP_REQUIRED -> Approval
        high_proposal = PurchaseProposalRequest(
            buyer_id="buy_user_high",
            merchant_id="mer_shop_1",
            mandate_id="man_buyer_1",
            operation=McpOperation.CREATE_ORDER,
            items=[
                CartItemProposal(
                    product_id="prd_2",
                    merchant_id="mer_shop_1",
                    name="4K Display Monitor",
                    category="electronics",
                    quantity=1,
                    unit_price_paise=1200000,
                )
            ],
            total_paise=1200000,
            currency=Currency.INR,
            idempotency_key="idemp_high_001",
        )
        tx_high = evaluate_purchase_proposal(high_proposal)
        self.assertEqual(tx_high.state, TransactionState.STEP_UP_REQUIRED)

        # Approve step-up
        tx_approved = approve_step_up(
            tx_high.transaction_id,
            StepUpApproveRequest(
                buyer_id="buy_user_high",
                transaction_id=tx_high.transaction_id,
                approved_amount_paise=1200000,
            ),
        )
        self.assertEqual(tx_approved.state, TransactionState.COMMITTED)

        # 3. Reject step-up
        tx_high2 = evaluate_purchase_proposal(
            PurchaseProposalRequest(
                buyer_id="buy_user_high",
                merchant_id="mer_shop_1",
                mandate_id="man_buyer_1",
                operation=McpOperation.CREATE_ORDER,
                items=[
                    CartItemProposal(
                        product_id="prd_3",
                        merchant_id="mer_shop_1",
                        name="Gaming Laptop",
                        category="electronics",
                        quantity=1,
                        unit_price_paise=1500000,
                    )
                ],
                total_paise=1500000,
                currency=Currency.INR,
                idempotency_key="idemp_high_002",
            )
        )
        tx_rejected = reject_step_up(
            tx_high2.transaction_id,
            StepUpRejectRequest(buyer_id="buy_user_high", reason="Too expensive"),
        )
        self.assertEqual(tx_rejected.state, TransactionState.REJECTED)

    def test_audit_and_receipt_endpoints(self) -> None:
        """Verify audit stream fetching and receipt verification."""
        events = get_transaction_events("tx_demo123")
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[0].transaction_id, "tx_demo123")

        receipt = get_receipt("rcpt_demo123")
        self.assertEqual(receipt.receipt_id, "rcpt_demo123")

        verify_res = verify_receipt_endpoint("rcpt_demo123")
        self.assertTrue(verify_res.is_valid)


if __name__ == "__main__":
    unittest.main()
