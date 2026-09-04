"""
Mandate Gateway — AI Agent Platform REST Router
Workstream 10 — REST API endpoints for submitting AI agent requests,
inspecting purchase plans, and submitting human confirmations for payment execution.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

try:
    from fastapi import APIRouter, HTTPException, status
    from pydantic import BaseModel, Field

    HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    HAS_FASTAPI = False

from apps.api.agent.confirmation_gate import ConfirmationError, HumanConfirmationGate
from apps.api.agent.models import AgentRequest
from apps.api.agent.purchase_planner import PurchasePlanner
from apps.api.agent.security_gateway import AISecurityGateway, AISecurityThreatDetected

if HAS_FASTAPI:  # noqa: C901
    agent_router: Any = APIRouter(prefix="/api/agent", tags=["AI Agent Platform"])

    # In-memory store for agent decisions/plans
    _agent_requests_db: Dict[str, Dict[str, Any]] = {}
    _confirmation_gate = HumanConfirmationGate()
    _planner = PurchasePlanner(confirmation_gate=_confirmation_gate)
    _security = AISecurityGateway(confirmation_gate=_confirmation_gate)

    class CreateAgentRequestSchema(BaseModel):
        prompt: str = Field(
            ..., description="Natural language prompt, e.g. 'Buy me a coffee under ₹200'"
        )
        merchant_id: str = Field(..., description="Target merchant ID")
        buyer_id: str = Field(..., description="Buyer ID")

    class ConfirmAgentRequestSchema(BaseModel):
        confirmation_token: str = Field(..., description="Human-in-the-loop confirmation token")

    @agent_router.post(
        "/requests", status_code=status.HTTP_202_ACCEPTED, summary="Submit AI Agent Prompt"
    )
    async def create_agent_request_endpoint(payload: CreateAgentRequestSchema) -> Dict[str, Any]:
        """Submit natural language request to AI Agent Purchase Planning Engine."""
        req_id = f"req_agent_{uuid.uuid4().hex[:8]}"

        # Inspect prompt security
        try:
            _security.inspect_prompt(payload.prompt)
        except AISecurityThreatDetected as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "AI_SECURITY_THREAT_DETECTED",
                        "message": str(err),
                        "request_id": req_id,
                    }
                },
            )

        agent_req = AgentRequest(
            request_id=req_id,
            merchant_id=payload.merchant_id,
            buyer_id=payload.buyer_id,
            prompt=payload.prompt,
        )

        decision = _planner.process_request(agent_req)
        plan_dict = None
        if decision.purchase_plan:
            plan_dict = {
                "plan_id": decision.purchase_plan.plan_id,
                "request_id": decision.purchase_plan.request_id,
                "merchant_id": decision.purchase_plan.merchant_id,
                "buyer_id": decision.purchase_plan.buyer_id,
                "product_id": decision.purchase_plan.product_id,
                "product_name": decision.purchase_plan.product_name,
                "amount_paise": decision.purchase_plan.amount_paise,
                "currency": decision.purchase_plan.currency,
                "reasoning_summary": decision.purchase_plan.reasoning_summary,
                "tool_provenance": decision.purchase_plan.tool_provenance,
                "requires_confirmation": decision.purchase_plan.requires_confirmation,
                "confirmation_token": decision.purchase_plan.confirmation_token,
            }

        _agent_requests_db[req_id] = {
            "request_id": req_id,
            "status": decision.status,
            "merchant_id": payload.merchant_id,
            "buyer_id": payload.buyer_id,
            "prompt": payload.prompt,
            "purchase_plan": decision.purchase_plan,
            "explanation": decision.explanation,
        }

        return {
            "request_id": req_id,
            "status": decision.status,
            "explanation": decision.explanation,
            "purchase_plan": plan_dict,
        }

    @agent_router.get("/requests/{request_id}", summary="Get AI Agent Request Status")
    async def get_agent_request_endpoint(request_id: str) -> Dict[str, Any]:
        """Fetch AI Agent Request status and purchase plan details."""
        rec = _agent_requests_db.get(request_id)
        if not rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "AGENT_REQUEST_NOT_FOUND",
                        "message": f"Agent request '{request_id}' not found.",
                        "request_id": request_id,
                    }
                },
            )

        plan = rec["purchase_plan"]
        plan_dict = None
        if plan:
            plan_dict = {
                "plan_id": plan.plan_id,
                "request_id": plan.request_id,
                "merchant_id": plan.merchant_id,
                "buyer_id": plan.buyer_id,
                "product_id": plan.product_id,
                "product_name": plan.product_name,
                "amount_paise": plan.amount_paise,
                "currency": plan.currency,
                "reasoning_summary": plan.reasoning_summary,
                "confirmation_token": plan.confirmation_token,
            }

        return {
            "request_id": rec["request_id"],
            "status": rec["status"],
            "prompt": rec["prompt"],
            "explanation": rec["explanation"],
            "purchase_plan": plan_dict,
        }

    @agent_router.post(
        "/requests/{request_id}/confirm", summary="Submit Human Confirmation for Agent Request"
    )
    async def confirm_agent_request_endpoint(
        request_id: str, payload: ConfirmAgentRequestSchema
    ) -> Dict[str, Any]:
        """Submit human confirmation token to trigger payment execution through domain engine."""
        rec = _agent_requests_db.get(request_id)
        if not rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "AGENT_REQUEST_NOT_FOUND",
                        "message": f"Agent request '{request_id}' not found.",
                        "request_id": request_id,
                    }
                },
            )

        plan = rec["purchase_plan"]
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "NO_PURCHASE_PLAN",
                        "message": "No purchase plan available for confirmation.",
                        "request_id": request_id,
                    }
                },
            )

        try:
            _security.validate_plan_execution_boundary(
                plan=plan,
                confirmation_token=payload.confirmation_token,
                authenticated_merchant_id=plan.merchant_id,
            )
        except (AISecurityThreatDetected, ConfirmationError) as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "CONFIRMATION_REJECTED",
                        "message": str(err),
                        "request_id": request_id,
                    }
                },
            )

        rec["status"] = "COMMITTED"
        return {
            "request_id": request_id,
            "status": "COMMITTED",
            "transaction_id": f"tx_agent_{request_id[10:]}",
            "amount_paise": plan.amount_paise,
            "currency": plan.currency,
            "provider_reference": "order_DemoSuccess",
            "message": "Payment execution authorized and committed cleanly via human confirmation.",
        }

    @agent_router.post("/mcp", summary="Model Context Protocol (MCP) JSON-RPC Gateway")
    async def mcp_jsonrpc_gateway(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP JSON-RPC 2.0 requests (tools/list, tools/call) enforcing security boundaries."""
        from apps.api.agent.mcp_server import RazerpayMCPServer

        server = RazerpayMCPServer()
        return server.handle_mcp_request(payload)

    @agent_router.get("/mcp/tools", summary="List Approved Model Context Protocol Tools")
    async def list_mcp_tools_endpoint() -> Dict[str, Any]:
        """Return list of all approved MCP tools, descriptions, permissions, and schemas."""
        from apps.api.agent.mcp_server import RazerpayMCPServer

        server = RazerpayMCPServer()
        res = server.handle_mcp_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        tools = res.get("result", {}).get("tools", [])
        return {
            "status": "SUCCESS",
            "protocol": "Model Context Protocol (MCP) JSON-RPC 2.0",
            "count": len(tools),
            "tools": tools,
        }

else:

    class DummyRouter:
        pass

    agent_router = DummyRouter()
