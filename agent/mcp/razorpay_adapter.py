"""
S02.5 — Razorpay Execution Rail MCP Adapter.

Translates pre-authorized Gateway decisions into official Razorpay MCP execution requests in test mode.
"""

from __future__ import annotations

from typing import Any

from agent.mcp.errors import McpErrorCode, McpGatewayError
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.tool_proxy import SecurityToolProxy
from apps.api.domain.types import McpOperation, PolicyDecision


class RazorpayMcpAdapter:
    """
    Adapter translating Gateway decisions into Razorpay MCP execution.

    Critical Rule:
    Does NOT make authorization decisions. Executes only Gateway-approved requests.
    """

    @classmethod
    def execute_mcp_tool(
        cls,
        tool_name: str,
        params: dict[str, Any],
        authorization: AuthorizationResult,
        execution_service: PaymentExecutionService | None = None,
    ) -> dict[str, Any]:
        """
        Execute an authorized MCP tool request against Razorpay execution rail.
        """
        if authorization.decision != PolicyDecision.ALLOW:
            raise McpGatewayError(
                McpErrorCode.MCP_TRANSACTION_UNAUTHORIZED,
                f"Cannot execute Razorpay tool {tool_name!r} without ALLOW authorization.",
            )

        if execution_service is not None:
            tool_proxy = SecurityToolProxy(execution_service)
            req = PaymentExecuteProposalRequest(
                authorization_id=str(params.get("authorization_id", "auth_default")),
                mandate_id=str(params.get("mandate_id", "mandate_default")),
                merchant_id=str(params.get("merchant_id", "merchant_default")),
                cart_hash=str(params.get("cart_hash", "0" * 64)),
                amount_paise=int(params.get("amount", 0)),
                currency=str(params.get("currency", "INR")),
                operation=McpOperation.from_str(tool_name),
            )
            resp = tool_proxy.proxy_execute_proposal(req)
            if not resp.success:
                raise McpGatewayError(
                    McpErrorCode.MCP_EXECUTION_FAILED,
                    f"Razorpay execution failed: {resp.error_detail or 'Unknown failure'}",
                )
            return {
                "success": True,
                "transaction_id": resp.transaction_id,
                "payment_state": resp.payment_state.value,
                "provider_reference": resp.provider_reference,
            }

        # Test Mode Fallback Execution Result
        return {
            "success": True,
            "status": "created",
            "tool": tool_name,
            "amount": int(params.get("amount", 0)),
            "currency": str(params.get("currency", "INR")),
            "provider_reference": f"pay_test_mcp_{tool_name}",
        }
