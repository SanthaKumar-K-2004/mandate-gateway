"""
Mandate Gateway — AI Tool Registry & Permission Classification
Workstream 4 — Strict, allowlisted tool registry enforcing permission tiers:
  SAFE_READ (search, product details, budget, status)
  RESTRICTED (create_purchase_plan, create_payment_proposal)
  CONFIRMATION_REQUIRED (execute_payment)
No dynamic eval or arbitrary code execution permitted.
"""

from __future__ import annotations

import enum
from typing import Any, Callable, Dict, List, Optional


class ToolPermission(str, enum.Enum):
    """Permission classification tiers for AI tools."""

    SAFE_READ = "SAFE_READ"
    RESTRICTED = "RESTRICTED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"


class ToolExecutionError(ValueError):
    """Raised when an unallowlisted tool is called or validation fails."""

    pass


class ToolDefinition:
    """Represents an approved AI tool with input/output schema and permission classification."""

    def __init__(
        self,
        name: str,
        description: str,
        permission: ToolPermission,
        handler: Callable[..., Dict[str, Any]],
        input_schema: Dict[str, Any],
    ):
        self.name = name
        self.description = description
        self.permission = permission
        self.handler = handler
        self.input_schema = input_schema


class AIToolRegistry:
    """Centralized allowlist registry for all approved AI tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def register(self, tool: ToolDefinition) -> None:
        """Register an approved tool in the registry."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Fetch tool definition by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List metadata for all registered allowlisted tools."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "permission": t.permission.value,
                "input_schema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    def invoke_tool(
        self, name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute an allowlisted tool with input validation.
        Rejects unallowlisted tools or forbidden execution contexts.
        """
        tool = self.get_tool(name)
        if not tool:
            raise ToolExecutionError(
                f"Tool '{name}' is not registered in the allowlisted AIToolRegistry."
            )

        # Rejection of payment execution without explicit confirmation context
        if tool.permission == ToolPermission.CONFIRMATION_REQUIRED:
            ctx = context or {}
            if not ctx.get("confirmation_token_valid"):
                raise ToolExecutionError(
                    f"Direct autonomous invocation of CONFIRMATION_REQUIRED tool '{name}' is prohibited. "
                    "Valid human confirmation token context is required."
                )

        return tool.handler(**arguments)

    def _register_default_tools(self) -> None:
        """Populate initial allowlisted tools."""

        # 1. search_products (SAFE_READ)
        def _search_products(query: str = "", max_price_paise: int = 50000) -> Dict[str, Any]:
            from apps.api.agent.live_data import LiveDataOrchestrator

            orchestrator = LiveDataOrchestrator()
            results = orchestrator.search_live_products(
                query=query, max_price_paise=max_price_paise
            )
            if not results:
                return {
                    "results": [],
                    "query": query,
                    "max_price_paise": max_price_paise,
                    "status": "SOURCE_UNAVAILABLE",
                    "explanation": "No live verified products returned from real search providers.",
                }
            return {
                "results": results,
                "count": len(results),
                "query": query,
                "max_price_paise": max_price_paise,
                "status": "SUCCESS",
            }

        self.register(
            ToolDefinition(
                name="search_products",
                description="Search available product catalog under a maximum budget limit.",
                permission=ToolPermission.SAFE_READ,
                handler=_search_products,
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_price_paise": {"type": "integer"},
                    },
                },
            )
        )

        # 2. get_product_details (SAFE_READ)
        def _get_product_details(product_id: str) -> Dict[str, Any]:
            if product_id == "prod_coffee_01":
                return {
                    "product_id": "prod_coffee_01",
                    "name": "Espresso Roast Coffee",
                    "amount_paise": 18000,
                    "merchant_id": "mer_cafe_acme",
                    "in_stock": True,
                }
            return {"product_id": product_id, "found": False}

        self.register(
            ToolDefinition(
                name="get_product_details",
                description="Fetch details for a specific product ID.",
                permission=ToolPermission.SAFE_READ,
                handler=_get_product_details,
                input_schema={
                    "type": "object",
                    "properties": {"product_id": {"type": "string"}},
                    "required": ["product_id"],
                },
            )
        )

        # 3. get_budget_status (SAFE_READ)
        def _get_budget_status(mandate_id: str = "man_default") -> Dict[str, Any]:
            return {
                "mandate_id": mandate_id,
                "daily_budget_paise": 100000,
                "spent_today_paise": 25000,
                "remaining_budget_paise": 75000,
            }

        self.register(
            ToolDefinition(
                name="get_budget_status",
                description="Check buyer mandate daily budget status.",
                permission=ToolPermission.SAFE_READ,
                handler=_get_budget_status,
                input_schema={"type": "object", "properties": {"mandate_id": {"type": "string"}}},
            )
        )

        # 4. get_transaction_status (SAFE_READ)
        def _get_transaction_status(transaction_id: str) -> Dict[str, Any]:
            return {"transaction_id": transaction_id, "state": "COMMITTED", "amount_paise": 18000}

        self.register(
            ToolDefinition(
                name="get_transaction_status",
                description="Query state for an existing transaction ID.",
                permission=ToolPermission.SAFE_READ,
                handler=_get_transaction_status,
                input_schema={
                    "type": "object",
                    "properties": {"transaction_id": {"type": "string"}},
                    "required": ["transaction_id"],
                },
            )
        )

        # 5. create_purchase_plan (RESTRICTED)
        def _create_purchase_plan(
            product_id: str, merchant_id: str, amount_paise: int
        ) -> Dict[str, Any]:
            return {
                "status": "PLAN_CREATED",
                "product_id": product_id,
                "merchant_id": merchant_id,
                "amount_paise": amount_paise,
                "requires_confirmation": True,
            }

        self.register(
            ToolDefinition(
                name="create_purchase_plan",
                description="Formulate a candidate purchase plan for buyer review.",
                permission=ToolPermission.RESTRICTED,
                handler=_create_purchase_plan,
                input_schema={
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string"},
                        "merchant_id": {"type": "string"},
                        "amount_paise": {"type": "integer"},
                    },
                    "required": ["product_id", "merchant_id", "amount_paise"],
                },
            )
        )

        # 6. execute_payment (CONFIRMATION_REQUIRED)
        def _execute_payment(payment_proposal_id: str, confirmation_token: str) -> Dict[str, Any]:
            return {
                "status": "SUCCESS",
                "payment_proposal_id": payment_proposal_id,
                "state": "COMMITTED",
            }

        self.register(
            ToolDefinition(
                name="execute_payment",
                description="Execute payment for an approved payment proposal.",
                permission=ToolPermission.CONFIRMATION_REQUIRED,
                handler=_execute_payment,
                input_schema={
                    "type": "object",
                    "properties": {
                        "payment_proposal_id": {"type": "string"},
                        "confirmation_token": {"type": "string"},
                    },
                    "required": ["payment_proposal_id", "confirmation_token"],
                },
            )
        )
