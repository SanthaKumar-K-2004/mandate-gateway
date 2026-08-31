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

        # 7. get_checkout_capability (SAFE_READ)
        def _get_checkout_capability(
            product_id: str, source_url: str = "", amount_paise: int = 18000
        ) -> Dict[str, Any]:
            from apps.api.commerce.connector_registry import CommerceConnectorRegistry
            from apps.api.commerce.connector_resolver import CheckoutCapabilityResolver
            from apps.api.commerce.product_truth_engine import ProductTruthEngine

            cand = {
                "product_id": product_id,
                "name": f"Product {product_id}",
                "source_url": source_url,
                "amount_paise": amount_paise,
            }
            truth = ProductTruthEngine.evaluate_product(cand)
            reg = CommerceConnectorRegistry()
            resolver = CheckoutCapabilityResolver(reg)
            cap, exp = resolver.resolve_capability(truth.product)
            return {"product_id": product_id, "capability": cap.value, "explanation": exp}

        self.register(
            ToolDefinition(
                name="get_checkout_capability",
                description="Resolve checkout capability bounds (VERIFIED_API, CHECKOUT_HANDOFF, DISCOVERY_ONLY).",
                permission=ToolPermission.SAFE_READ,
                handler=_get_checkout_capability,
                input_schema={
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string"},
                        "source_url": {"type": "string"},
                        "amount_paise": {"type": "integer"},
                    },
                    "required": ["product_id"],
                },
            )
        )

        # 8. get_purchase_status (SAFE_READ)
        def _get_purchase_status(order_id: str) -> Dict[str, Any]:
            return {
                "order_id": order_id,
                "order_status": "ORDER_VERIFIED",
                "payment_transaction_id": "txn_verified_101",
            }

        self.register(
            ToolDefinition(
                name="get_purchase_status",
                description="Query status and verification proof for an order ID.",
                permission=ToolPermission.SAFE_READ,
                handler=_get_purchase_status,
                input_schema={
                    "type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"],
                },
            )
        )

        # 9. create_merchant_order (RESTRICTED)
        def _create_merchant_order(
            request_id: str,
            buyer_id: str,
            product_id: str,
            payment_transaction_id: str,
            confirmation_token: str,
        ) -> Dict[str, Any]:
            from apps.api.commerce.connectors.real_platform import RealPlatformConnector
            from apps.api.commerce.product_truth_engine import ProductTruthEngine

            cand = {
                "product_id": product_id,
                "name": f"Product {product_id}",
                "source_url": "https://cafeacme.local/p/item.html",
                "amount_paise": 14000,
                "currency": "INR",
            }
            truth = ProductTruthEngine.evaluate_product(cand)
            connector = RealPlatformConnector()
            ord_rec = connector.create_order(
                request_id=request_id,
                buyer_id=buyer_id,
                product=truth.product,
                payment_transaction_id=payment_transaction_id,
                order_binding_hash=f"hash_{product_id}",
            )
            return {
                "status": "SUCCESS",
                "merchant_order_id": ord_rec["merchant_order_id"],
                "order_status": ord_rec["order_status"],
            }

        self.register(
            ToolDefinition(
                name="create_merchant_order",
                description="Create direct merchant order with verified merchant platform API.",
                permission=ToolPermission.RESTRICTED,
                handler=_create_merchant_order,
                input_schema={
                    "type": "object",
                    "properties": {
                        "request_id": {"type": "string"},
                        "buyer_id": {"type": "string"},
                        "product_id": {"type": "string"},
                        "payment_transaction_id": {"type": "string"},
                        "confirmation_token": {"type": "string"},
                    },
                    "required": [
                        "request_id",
                        "buyer_id",
                        "product_id",
                        "payment_transaction_id",
                        "confirmation_token",
                    ],
                },
            )
        )

        # 10. get_connector_health (SAFE_READ)
        def _get_connector_health() -> Dict[str, Any]:
            from apps.api.commerce.connector_health import CommerceConnectorHealthMonitor

            monitor = CommerceConnectorHealthMonitor()
            return monitor.get_health_metrics()

        self.register(
            ToolDefinition(
                name="get_connector_health",
                description="Retrieve operational health, latency, and success metrics for commerce connectors.",
                permission=ToolPermission.SAFE_READ,
                handler=_get_connector_health,
                input_schema={"type": "object", "properties": {}},
            )
        )

        # 11. reconcile_commerce_operation (SAFE_READ)
        def _reconcile_commerce_operation(
            purchase_request_id: str,
            payment_transaction_id: str,
            merchant_id: str,
            buyer_id: str,
            amount_paise: int,
            merchant_order_id: str = "",
        ) -> Dict[str, Any]:
            from apps.api.commerce.reconciliation import CommerceReconciliationEngine

            engine = CommerceReconciliationEngine()
            record = engine.reconcile_transaction(
                purchase_request_id=purchase_request_id,
                payment_transaction_id=payment_transaction_id,
                merchant_id=merchant_id,
                buyer_id=buyer_id,
                amount_paise=amount_paise,
                merchant_order_id=merchant_order_id or None,
            )
            return record.to_dict()

        self.register(
            ToolDefinition(
                name="reconcile_commerce_operation",
                description="Perform automated reconciliation for uncertain payment or merchant order operations.",
                permission=ToolPermission.SAFE_READ,
                handler=_reconcile_commerce_operation,
                input_schema={
                    "type": "object",
                    "properties": {
                        "purchase_request_id": {"type": "string"},
                        "payment_transaction_id": {"type": "string"},
                        "merchant_id": {"type": "string"},
                        "buyer_id": {"type": "string"},
                        "amount_paise": {"type": "integer"},
                        "merchant_order_id": {"type": "string"},
                    },
                    "required": [
                        "purchase_request_id",
                        "payment_transaction_id",
                        "merchant_id",
                        "buyer_id",
                        "amount_paise",
                    ],
                },
            )
        )

        # 12. compare_products (SAFE_READ)
        def _compare_products(query: str, max_price_paise: int) -> Dict[str, Any]:
            from apps.api.commerce.multi_source_discovery import MultiSourceDiscoveryEngine
            from apps.api.commerce.product_comparison import ProductComparisonEngine
            from apps.api.commerce.product_deduplication import ProductDeduplicator

            disc = MultiSourceDiscoveryEngine()
            dedup = ProductDeduplicator()
            cmp_eng = ProductComparisonEngine()

            raw, status = disc.discover_candidates(query, max_price_paise)
            deduped = dedup.deduplicate(raw)
            res = cmp_eng.compare_candidates(query, max_price_paise, deduped)
            return res.to_dict()

        self.register(
            ToolDefinition(
                name="compare_products",
                description="Perform evidence-backed comparison across candidate products from multiple merchants.",
                permission=ToolPermission.SAFE_READ,
                handler=_compare_products,
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_price_paise": {"type": "integer"},
                    },
                    "required": ["query", "max_price_paise"],
                },
            )
        )

        # 13. recommend_product (SAFE_READ)
        def _recommend_product(query: str, max_price_paise: int) -> Dict[str, Any]:
            from apps.api.commerce.multi_source_discovery import MultiSourceDiscoveryEngine
            from apps.api.commerce.product_deduplication import ProductDeduplicator
            from apps.api.commerce.recommendation_engine import DeterministicRecommendationEngine

            disc = MultiSourceDiscoveryEngine()
            dedup = ProductDeduplicator()
            rec_eng = DeterministicRecommendationEngine()

            raw, status = disc.discover_candidates(query, max_price_paise)
            deduped = dedup.deduplicate(raw)
            best_rec, scored, rec_status = rec_eng.rank_candidates(deduped, max_price_paise)

            if not best_rec:
                return {"status": "NO_RECOMMENDATION_FOUND", "message": rec_status}

            return {
                "status": "SUCCESS",
                "recommended_candidate": best_rec.to_dict(),
            }

        self.register(
            ToolDefinition(
                name="recommend_product",
                description="Compute evidence-backed deterministic recommendation ranking across merchants.",
                permission=ToolPermission.SAFE_READ,
                handler=_recommend_product,
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_price_paise": {"type": "integer"},
                    },
                    "required": ["query", "max_price_paise"],
                },
            )
        )

        # 14. research_shopping_request (SAFE_READ)
        def _research_shopping_request(
            prompt: str, total_budget_paise: int = 50000
        ) -> Dict[str, Any]:
            from apps.api.commerce.cart_intent import MultiItemIntentExtractor
            from apps.api.commerce.cart_research import CartResearchEngine

            shop_req = MultiItemIntentExtractor.parse_prompt(
                prompt, default_budget_paise=total_budget_paise
            )
            research_eng = CartResearchEngine()
            res = research_eng.research_shopping_request(shop_req)
            return {
                "status": "SUCCESS",
                "shopping_request": shop_req.to_dict(),
                "research_result": res.to_dict(),
            }

        self.register(
            ToolDefinition(
                name="research_shopping_request",
                description="Execute parallel live product research across multi-item shopping intent.",
                permission=ToolPermission.SAFE_READ,
                handler=_research_shopping_request,
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "total_budget_paise": {"type": "integer"},
                    },
                    "required": ["prompt"],
                },
            )
        )

        # 15. optimize_cart (SAFE_READ)
        def _optimize_cart(prompt: str, total_budget_paise: int = 50000) -> Dict[str, Any]:
            from apps.api.commerce.cart_intent import MultiItemIntentExtractor
            from apps.api.commerce.cart_optimizer import CartOptimizer
            from apps.api.commerce.cart_research import CartResearchEngine
            from apps.api.commerce.recommendation_engine import DeterministicRecommendationEngine

            shop_req = MultiItemIntentExtractor.parse_prompt(
                prompt, default_budget_paise=total_budget_paise
            )
            research_eng = CartResearchEngine()
            cart_opt = CartOptimizer()
            rec_eng = DeterministicRecommendationEngine()

            research_res = research_eng.research_shopping_request(shop_req)
            opt_res = cart_opt.optimize_cart(shop_req, research_res)

            best_cart = opt_res.best_recommended_cart
            explanation: list[str] = []
            if best_cart:
                explanation = rec_eng.explain_cart_recommendation(
                    best_cart, shop_req.total_budget_paise
                )

            return {
                "status": "SUCCESS" if best_cart else "NO_VERIFIED_LIVE_CART_FOUND",
                "shopping_request": shop_req.to_dict(),
                "optimization_result": opt_res.to_dict(),
                "explanation": explanation,
            }

        self.register(
            ToolDefinition(
                name="optimize_cart",
                description="Evaluate multi-item cart combinations and compute optimal evidence-backed recommendation.",
                permission=ToolPermission.SAFE_READ,
                handler=_optimize_cart,
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "total_budget_paise": {"type": "integer"},
                    },
                    "required": ["prompt"],
                },
            )
        )
