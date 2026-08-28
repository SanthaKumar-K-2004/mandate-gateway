"""
S03.1 — Control Center Concurrency Test Suite.

Verifies thread safety across REST API endpoints using 20 concurrent worker threads.
"""

from __future__ import annotations

import concurrent.futures
from datetime import datetime, timedelta, timezone
import unittest
import uuid

from apps.api.contracts.mandate import MandateCreate
from apps.api.contracts.merchant import MerchantCreate
from apps.api.contracts.product import ProductCreateRequest
from apps.api.contracts.transaction import CartItemProposal, PurchaseProposalRequest
from apps.api.domain.types import Currency, McpOperation
from apps.api.routers.mandates import create_mandate
from apps.api.routers.merchants import create_merchant
from apps.api.routers.products import create_product
from apps.api.routers.transactions import evaluate_purchase_proposal


class TestControlCenterConcurrency(unittest.TestCase):
    """Concurrency test cases for S03.1 Control Center REST routers."""

    def test_parallel_merchant_product_and_proposal_creation(self) -> None:
        """Verify 20 concurrent workers creating merchants, products, mandates, and proposals."""
        merchant = create_merchant(
            MerchantCreate(name="Concurrent Store", razorpay_account_id="acc_conc1")
        )

        def worker_task(index: int) -> str:
            # 1. Create product
            prod = create_product(
                merchant.merchant_id,
                ProductCreateRequest(
                    name=f"Concurrent Product {index}",
                    category="electronics",
                    price_paise=100000 + index * 1000,
                    stock_quantity=100,
                ),
            )
            # 2. Create mandate
            mandate = create_mandate(
                MandateCreate(
                    buyer_id=f"buy_conc_{index}",
                    merchant_scope={merchant.merchant_id},
                    category_scope={"electronics"},
                    maximum_amount_paise=500000,
                    daily_budget_paise=1000000,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                )
            )
            # 3. Evaluate proposal
            tx = evaluate_purchase_proposal(
                PurchaseProposalRequest(
                    buyer_id=f"buy_conc_{index}",
                    merchant_id=merchant.merchant_id,
                    mandate_id=mandate.mandate_id,
                    operation=McpOperation.CREATE_ORDER,
                    items=[
                        CartItemProposal(
                            product_id=prod.product_id,
                            merchant_id=merchant.merchant_id,
                            name=prod.name,
                            category=prod.category,
                            quantity=1,
                            unit_price_paise=prod.price_paise,
                        )
                    ],
                    total_paise=prod.price_paise,
                    currency=Currency.INR,
                    idempotency_key=f"idemp_conc_{index}_{uuid.uuid4().hex[:6]}",
                )
            )
            return str(tx.transaction_id)

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker_task, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.assertEqual(len(results), 20)
        self.assertEqual(len(set(results)), 20)  # All transaction IDs must be unique


if __name__ == "__main__":
    unittest.main()
