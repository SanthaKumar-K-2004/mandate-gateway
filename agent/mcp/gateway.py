"""
S02.5 — Stateful MCP Security Gateway & Reverse Proxy.

Handles JSON-RPC 2.0 tools/list filtering and tools/call runtime authorization dispatching.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Set

from agent.mcp.authorization import McpRuntimeAuthorizer
from agent.mcp.errors import McpErrorCode, McpGatewayError
from agent.mcp.masking import McpToolMasker
from agent.mcp.observability import McpAuditLogger
from agent.mcp.razorpay_adapter import RazorpayMcpAdapter
from agent.mcp.types import McpJsonRpcRequest, McpJsonRpcResponse
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.types import McpOperation, PolicyDecision


class McpSecurityGateway:
    """
    Stateful MCP Security Reverse Proxy.

    Responsibilities:
    1. Response to tools/list with filtered, masked tools.
    2. Authoritative interception of tools/call to block hidden/unauthorized tools.
    3. JSON-RPC 2.0 protocol error handling.
    """

    def __init__(
        self,
        masker: McpToolMasker | None = None,
        authorizer: McpRuntimeAuthorizer | None = None,
    ) -> None:
        self.masker: McpToolMasker = masker or McpToolMasker()
        self.authorizer: McpRuntimeAuthorizer = authorizer or McpRuntimeAuthorizer(self.masker)
        self._lock: threading.RLock = threading.RLock()

    def handle_tools_list(
        self,
        request: McpJsonRpcRequest,
        allowed_operations: Set[McpOperation],
        blocked_operations: Set[McpOperation],
        session_id: str = "default",
    ) -> McpJsonRpcResponse:
        """
        Handle tools/list request by returning dynamically masked tools list.
        """
        with self._lock:
            McpAuditLogger.log_event("tools_list_requested", session_id=session_id)
            filtered_tools = self.masker.filter_tools_for_scope(
                allowed_operations=allowed_operations,
                blocked_operations=blocked_operations,
            )

            tools_payload = [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.inputSchema,
                }
                for t in filtered_tools
            ]

            McpAuditLogger.log_event("tools_list_filtered", session_id=session_id)
            return McpJsonRpcResponse(id=request.id, result={"tools": tools_payload})

    def handle_tools_call(
        self,
        request: McpJsonRpcRequest,
        allowed_operations: Set[McpOperation],
        blocked_operations: Set[McpOperation],
        gateway_authorization: AuthorizationResult | None = None,
        execution_service: PaymentExecutionService | None = None,
        session_id: str = "default",
    ) -> McpJsonRpcResponse:
        """
        Handle tools/call request with authoritative runtime authorization checks.
        """
        with self._lock:
            McpAuditLogger.log_event("tools_call_requested", session_id=session_id)
            params = request.params or {}
            name = str(params.get("name", "")).strip()
            arguments = params.get("arguments", {})

            if not name:
                return McpJsonRpcResponse(
                    id=request.id,
                    error={
                        "code": -32602,
                        "message": "Missing mandatory parameter 'name' in tools/call.",
                    },
                )

            is_authorized = (
                gateway_authorization is not None
                and gateway_authorization.decision == PolicyDecision.ALLOW
            )

            # 1. Authoritative Runtime Check (Blocks hidden or unauthorized tools)
            try:
                self.authorizer.authorize_tool_call(
                    tool_name=name,
                    allowed_operations=allowed_operations,
                    blocked_operations=blocked_operations,
                    gateway_authorized=is_authorized,
                    session_id=session_id,
                )
            except McpGatewayError as mge:
                return McpJsonRpcResponse(
                    id=request.id,
                    error={
                        "code": -32001,
                        "message": mge.detail,
                        "data": {"error_code": mge.code.value},
                    },
                )

            # 2. Execute via Razorpay Execution Rail Adapter
            assert gateway_authorization is not None
            try:
                exec_result = RazorpayMcpAdapter.execute_mcp_tool(
                    tool_name=name,
                    params=arguments,
                    authorization=gateway_authorization,
                    execution_service=execution_service,
                )
                McpAuditLogger.log_event(
                    "execution_completed", tool_name=name, session_id=session_id
                )
                return McpJsonRpcResponse(
                    id=request.id,
                    result={"content": [{"type": "text", "text": json.dumps(exec_result)}]},
                )
            except McpGatewayError as mge:
                return McpJsonRpcResponse(
                    id=request.id,
                    error={
                        "code": -32603,
                        "message": mge.detail,
                        "data": {"error_code": mge.code.value},
                    },
                )

    def dispatch(
        self,
        raw_payload: str | dict[str, Any],
        allowed_operations: Set[McpOperation],
        blocked_operations: Set[McpOperation],
        gateway_authorization: AuthorizationResult | None = None,
        execution_service: PaymentExecutionService | None = None,
        session_id: str = "default",
    ) -> dict[str, Any]:
        """
        Dispatch raw JSON or dictionary JSON-RPC 2.0 payload to appropriate handler.
        """
        if isinstance(raw_payload, str):
            try:
                data = json.loads(raw_payload)
            except Exception:
                return McpJsonRpcResponse(
                    id=None,
                    error={"code": -32700, "message": "Parse error: Invalid JSON payload."},
                ).to_dict()
        elif isinstance(raw_payload, dict):
            data = raw_payload
        else:
            return McpJsonRpcResponse(
                id=None,
                error={"code": -32600, "message": "Invalid Request: Payload must be JSON object."},
            ).to_dict()

        if not isinstance(data, dict) or data.get("jsonrpc") != "2.0":
            return McpJsonRpcResponse(
                id=data.get("id") if isinstance(data, dict) else None,
                error={"code": -32600, "message": "Invalid Request: Missing or invalid 'jsonrpc' field."},
            ).to_dict()

        method = data.get("method")
        req_id = data.get("id")
        params = data.get("params", {})
        if not isinstance(params, dict):
            params = {}

        req = McpJsonRpcRequest(method=str(method), params=params, id=req_id)

        if method == "tools/list":
            resp = self.handle_tools_list(
                request=req,
                allowed_operations=allowed_operations,
                blocked_operations=blocked_operations,
                session_id=session_id,
            )
            return resp.to_dict()
        elif method == "tools/call":
            resp = self.handle_tools_call(
                request=req,
                allowed_operations=allowed_operations,
                blocked_operations=blocked_operations,
                gateway_authorization=gateway_authorization,
                execution_service=execution_service,
                session_id=session_id,
            )
            return resp.to_dict()
        else:
            return McpJsonRpcResponse(
                id=req_id,
                error={"code": -32601, "message": f"Method '{method}' not found."},
            ).to_dict()
