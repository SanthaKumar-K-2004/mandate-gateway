"""
S02.5 — MCP Security Gateway Integration Tests.

Verifies end-to-end integration from tools/list filtering to PolicyEngine authorization and Razorpay MCP execution.
"""

from datetime import datetime, timezone
import unittest

from agent.mcp.gateway import McpSecurityGateway
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.domain.cart import CartItem
from apps.api.domain.cart_integrity import build_cart_with_hash
from apps.api.domain.mandates import SpendingLimits, create_buyer_mandate
from apps.api.domain.merchant_policy import create_merchant_policy
from apps.api.domain.policy_engine import PolicyEngine
from apps.api.domain.types import Currency, McpOperation, PolicyDecision


class TestMcpIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = McpSecurityGateway()
        self.buyer_id = "buyer_mcp_integ_001"
        self.merchant_id = "merchant_mcp_integ_001"
        self.mandate_id = "mandate_mcp_integ_001"

        self.allowed_ops = {
            McpOperation.CREATE_ORDER,
            McpOperation.CREATE_PAYMENT_LINK,
            McpOperation.FETCH_PAYMENT,
        }
        self.blocked_ops = {
            McpOperation.PAYOUT,
            McpOperation.SETTLEMENT,
            McpOperation.BANK_TRANSFER,
        }

        self.mandate = create_buyer_mandate(
            mandate_id=self.mandate_id,
            buyer_id=self.buyer_id,
            limits=SpendingLimits(
                per_tx_paise=5000000,
                daily_paise=10000000,
                monthly_paise=50000000,
            ),
        )

        self.merchant_policy = create_merchant_policy(
            merchant_id=self.merchant_id,
            allowed_categories=frozenset({"electronics"}),
        )

    def test_end_to_end_mcp_gateway_flow(self) -> None:
        """Verify tools/list filtering, PolicyEngine evaluation, and tools/call execution."""
        # 1. Query tools/list via Gateway
        list_req = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        list_resp = self.gateway.dispatch(
            raw_payload=list_req,
            allowed_operations=self.allowed_ops,
            blocked_operations=self.blocked_ops,
        )
        self.assertIn("result", list_resp)
        tools = [t["name"] for t in list_resp["result"]["tools"]]
        self.assertEqual(sorted(tools), ["create_order", "create_payment_link", "fetch_payment"])

        # 2. Build Cart & Evaluate PolicyEngine
        item = CartItem(
            product_id="prod_monitor",
            merchant_id=self.merchant_id,
            name="4K Monitor",
            category="electronics",
            quantity=1,
            unit_price_paise=3500000,
            currency=Currency.INR,
        )
        cart = build_cart_with_hash(
            merchant_id=self.merchant_id,
            mandate_id=self.mandate_id,
            currency=Currency.INR,
            items=(item,),
            total_paise=3500000,
        )

        policy_eval = PolicyEngine.evaluate(
            mandate=self.mandate,
            merchant_policy=self.merchant_policy,
            cart=cart,
            operation=McpOperation.CREATE_ORDER,
            at=datetime.now(timezone.utc),
        )

        self.assertEqual(policy_eval.decision, PolicyDecision.ALLOW)

        auth_result = AuthorizationResult(
            decision=policy_eval.decision,
        )

        # 3. Call tools/call via Gateway
        call_req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "create_order", "arguments": {"amount": 3500000}},
            "id": 2,
        }

        call_resp = self.gateway.dispatch(
            raw_payload=call_req,
            allowed_operations=self.allowed_ops,
            blocked_operations=self.blocked_ops,
            gateway_authorization=auth_result,
        )

        self.assertIn("result", call_resp)
        self.assertIn("content", call_resp["result"])
        self.assertEqual(call_resp["result"]["content"][0]["type"], "text")


if __name__ == "__main__":
    unittest.main()
