"""
Adversarial Security Test Matrix for M26 (Public Platform Integration, MCP Client Interoperability, Live Pilot).
"""

from __future__ import annotations

import unittest

from apps.api.agent.mcp_server import RazerpayMCPServer
from apps.api.commerce.connectors.base import CommerceConnectorError
from apps.api.commerce.connectors.public_platform import PublicPlatformConnector
from apps.api.commerce.product_truth_engine import ProductTruthEngine


class TestM26AdversarialSecurity(unittest.TestCase):
    """Adversarial Security Test Suite for M26 features."""

    def test_adv_01_mcp_autonomous_payment_tool_exclusion(self) -> None:
        """Verify autonomous direct payment tools are strictly excluded from MCP tools/list."""
        server = RazerpayMCPServer()
        resp = server.handle_mcp_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        self.assertNotIn("execute_payment", tool_names)
        self.assertNotIn("execute_confirmed_purchase", tool_names)

    def test_adv_02_public_connector_missing_payment_id_rejected(self) -> None:
        """Verify public connector raises CommerceConnectorError if payment transaction ID is missing."""
        connector = PublicPlatformConnector()
        truth = ProductTruthEngine.evaluate_product(
            {
                "product_id": "prod_off_01",
                "name": "Coffee",
                "source_url": "https://world.openfoodfacts.org/product/c.html",
                "amount_paise": 18000,
            }
        )

        with self.assertRaises(CommerceConnectorError):
            connector.create_order(
                request_id="req_adv_02",
                buyer_id="buyer_adv",
                product=truth.product,
                payment_transaction_id="",  # Empty payment ID!
                order_binding_hash="hash_02",
            )
