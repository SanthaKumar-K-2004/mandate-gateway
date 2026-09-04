#!/usr/bin/env python3
"""
Mandate Gateway — External MCP Client Interoperability Test Runner (M26)
Workstream 3 — Simulates an external Model Context Protocol (MCP) client
communicating via JSON-RPC 2.0 with RazorpayMCPServer.
"""

from __future__ import annotations

import sys
from typing import Any, Dict

from apps.api.agent.mcp_server import RazorpayMCPServer


def run_mcp_client_interoperability_suite() -> int:
    """Execute complete external MCP protocol interoperability test suite."""
    print("============================================================")
    print(" Mandate Gateway — External MCP Client Interoperability Suite")
    print("============================================================")

    server = RazorpayMCPServer()

    # Step 1: Execute 'tools/list' JSON-RPC call
    print("\n[Step 1] Sending 'tools/list' JSON-RPC request...")
    list_request: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 101,
        "method": "tools/list",
    }
    list_resp = server.handle_mcp_request(list_request)
    assert list_resp.get("jsonrpc") == "2.0"
    assert "result" in list_resp
    tools = list_resp["result"].get("tools", [])
    tool_names = [t["name"] for t in tools]

    print(f" -> Discovered {len(tools)} MCP tools: {', '.join(tool_names)}")

    # Security Invariant Check: execute_payment MUST NOT be in tools/list
    assert (
        "execute_payment" not in tool_names
    ), "CRITICAL SECURITY FAILURE: execute_payment exposed in tools/list!"
    assert (
        "execute_confirmed_purchase" not in tool_names
    ), "CRITICAL SECURITY FAILURE: direct payment execution exposed!"
    print(
        " [✓] Security Check Passed: Autonomous direct payment tools strictly excluded from tools/list."
    )

    # Step 2: Execute 'tools/call' for 'search_products'
    print("\n[Step 2] Executing 'tools/call' for 'search_products'...")
    call_req1: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 102,
        "method": "tools/call",
        "params": {
            "name": "search_products",
            "arguments": {"query": "coffee", "max_price_paise": 20000},
        },
    }
    call_resp1 = server.handle_mcp_request(call_req1)
    assert "result" in call_resp1
    print(f" -> Call Result Success: {call_resp1['result']['content'][0]['text'][:80]}...")

    # Step 3: Execute 'tools/call' for 'get_checkout_capability'
    print("\n[Step 3] Executing 'tools/call' for 'get_checkout_capability'...")
    call_req2: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 103,
        "method": "tools/call",
        "params": {
            "name": "get_checkout_capability",
            "arguments": {
                "product_id": "prod_off_coffee_250",
                "source_url": "https://world.openfoodfacts.org/product/espresso_coffee.html",
                "amount_paise": 18000,
            },
        },
    }
    call_resp2 = server.handle_mcp_request(call_req2)
    assert "result" in call_resp2
    print(f" -> Capability Result: {call_resp2['result']['content'][0]['text'][:80]}...")

    # Step 4: Execute 'tools/call' for 'get_connector_health'
    print("\n[Step 4] Executing 'tools/call' for 'get_connector_health'...")
    call_req3: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 104,
        "method": "tools/call",
        "params": {
            "name": "get_connector_health",
            "arguments": {},
        },
    }
    call_resp3 = server.handle_mcp_request(call_req3)
    assert "result" in call_resp3
    print(f" -> Connector Health Result: {call_resp3['result']['content'][0]['text'][:80]}...")

    # Step 5: Verify direct execution barrier rejection for restricted tool invocation via 'tools/call'
    print("\n[Step 5] Testing direct 'tools/call' for restricted tool 'execute_payment'...")
    call_req4: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 105,
        "method": "tools/call",
        "params": {
            "name": "execute_payment",
            "arguments": {"payment_proposal_id": "prop_123", "confirmation_token": "token_123"},
        },
    }
    call_resp4 = server.handle_mcp_request(call_req4)
    assert (
        "error" in call_resp4
    ), "CRITICAL SECURITY FAILURE: execute_payment direct invocation was not blocked!"
    assert "Security Rejection" in call_resp4["error"]["message"]
    print(" -> Direct Restricted Call Rejection verified:", call_resp4["error"]["message"])

    print("\n============================================================")
    print(" [✓] EXTERNAL MCP CLIENT INTEROPERABILITY SUITE PASSED CLEANLY!")
    print("============================================================")
    return 0


if __name__ == "__main__":
    sys.exit(run_mcp_client_interoperability_suite())
