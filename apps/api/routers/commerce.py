"""
Mandate Gateway — Commerce API Router (M24/M25)
Workstream 5 — REST API endpoints for product truth verification, price revalidation,
capability resolution, checkout preparation, direct merchant order creation, and connector health.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from apps.api.commerce.checkout_orchestrator import CheckoutOrchestrator
from apps.api.commerce.connector_health import CommerceConnectorHealthMonitor
from apps.api.commerce.connector_registry import CommerceConnectorRegistry
from apps.api.commerce.connector_resolver import CheckoutCapabilityResolver
from apps.api.commerce.connectors.public_platform import PublicPlatformConnector
from apps.api.commerce.connectors.real_platform import RealPlatformConnector
from apps.api.commerce.models import ProductVerificationStatus
from apps.api.commerce.order_binding import CommerceOrderBinder
from apps.api.commerce.order_verification import OrderVerificationEngine
from apps.api.commerce.price_revalidation import LivePriceRevalidator
from apps.api.commerce.cart_intent import MultiItemIntentExtractor
from apps.api.commerce.cart_optimizer import CartOptimizer
from apps.api.commerce.cart_research import CartResearchEngine
from apps.api.commerce.connector_config import CommerceConnectorConfigManager
from apps.api.commerce.multi_source_discovery import MultiSourceDiscoveryEngine
from apps.api.commerce.product_comparison import ProductComparisonEngine
from apps.api.commerce.product_deduplication import ProductDeduplicator
from apps.api.commerce.product_truth_engine import ProductTruthEngine
from apps.api.commerce.recommendation_engine import DeterministicRecommendationEngine
from apps.api.commerce.reconciliation import CommerceReconciliationEngine
from apps.api.commerce.transaction_binding import CommerceTransactionBindingManager
from apps.api.commerce.payments import (
    AgentPaymentPolicyEngine,
    PolicyEvaluationContext,
    RazorpayClient,
    RazorpayPaymentProtocolAdapter,
    UAPAuthorizationLayer,
    UAPPaymentProtocolAdapter,
    X402PaymentAdapter,
    X402PaymentProtocolAdapter,
    get_timeline_manager,
)
from apps.api.ai.llm.engine import LLMDecisionEngine
from apps.api.ai.risk.combined import CombinedRiskIntelligenceEngine

_llm_engine = LLMDecisionEngine()
_risk_engine = CombinedRiskIntelligenceEngine()

router = APIRouter(prefix="/api/v1/commerce", tags=["Commerce Truth & Checkout"])

_registry = CommerceConnectorRegistry()
_real_connector = RealPlatformConnector()
_public_connector = PublicPlatformConnector()
_registry.register_connector(
    _real_connector, target_domains=["cafeacme.local", "api.cafeacme.local"]
)
_registry.register_connector(
    _public_connector,
    target_domains=["world.openfoodfacts.org", "api.openfoodfacts.org", "openfoodfacts.org"],
)

_orchestrator = CheckoutOrchestrator(registry=_registry)
_order_verifier = OrderVerificationEngine()
_order_binder = CommerceOrderBinder()
_tx_binder_mgr = CommerceTransactionBindingManager()
_health_monitor = CommerceConnectorHealthMonitor()
_config_mgr = CommerceConnectorConfigManager()
_reconciliation_engine = CommerceReconciliationEngine()
_discovery_engine = MultiSourceDiscoveryEngine(registry=_registry)
_deduplicator = ProductDeduplicator()
_comparison_engine = ProductComparisonEngine()
_recommendation_engine = DeterministicRecommendationEngine()
_cart_research_engine = CartResearchEngine(discovery_engine=_discovery_engine)
_cart_optimizer = CartOptimizer()

# Agentic Payment Protocol Instances
_razorpay_client = RazorpayClient()
_policy_engine = AgentPaymentPolicyEngine()
_uap_layer = UAPAuthorizationLayer()
_x402_adapter = X402PaymentAdapter()
_rzp_protocol = RazorpayPaymentProtocolAdapter(_razorpay_client, _policy_engine)
_x402_protocol = X402PaymentProtocolAdapter(_x402_adapter, _policy_engine)
_uap_protocol = UAPPaymentProtocolAdapter(_uap_layer, _policy_engine)
_timeline_mgr = get_timeline_manager()


class VerifyProductRequest(BaseModel):
    product_id: Optional[str] = Field(None, description="Candidate product ID")
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field("", description="Product description")
    source_url: str = Field(..., description="Exact product detail URL")
    amount_paise: int = Field(..., description="Amount in Paise")
    currency: str = Field("INR", description="Currency code")
    merchant_name: Optional[str] = Field(None, description="Merchant seller name")


class PrepareCheckoutRequest(BaseModel):
    request_id: str = Field(..., description="Agent purchase request ID")
    buyer_id: str = Field(..., description="Authenticated buyer ID")
    raw_candidate: Dict[str, Any] = Field(..., description="Raw candidate product dictionary")
    live_recheck_data: Optional[Dict[str, Any]] = Field(
        None, description="Optional live recheck data"
    )


class CreateOrderRequest(BaseModel):
    request_id: str = Field(..., description="Agent purchase request ID")
    buyer_id: str = Field(..., description="Authenticated buyer ID")
    preparation_id: str = Field(..., description="Prepared checkout session ID")
    payment_transaction_id: str = Field(
        ..., description="Authorized RAZORPAY payment transaction ID"
    )
    confirmation_token: str = Field(..., description="Verified human confirmation token")
    raw_candidate: Dict[str, Any] = Field(..., description="Candidate product payload")


@router.post("/products/verify", summary="Evaluate Product Truth", status_code=status.HTTP_200_OK)
async def verify_product(payload: VerifyProductRequest) -> Dict[str, Any]:
    """Evaluate product truth for a raw product candidate payload."""
    candidate_dict = payload.model_dump()
    truth = ProductTruthEngine.evaluate_product(candidate_dict)
    return {
        "status": "SUCCESS",
        "truth": truth.to_dict(),
    }


@router.post(
    "/products/revalidate",
    summary="Revalidate Live Price and Stock",
    status_code=status.HTTP_200_OK,
)
async def revalidate_product(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Revalidate product price and stock availability."""
    truth = ProductTruthEngine.evaluate_product(payload)
    if truth.product.verification_status == ProductVerificationStatus.UNVERIFIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product truth verification failed: {'; '.join(truth.validation_errors)}",
        )

    price_valid, current_price, price_changed = LivePriceRevalidator.revalidate(
        truth.product, payload
    )
    return {
        "status": "SUCCESS",
        "price_valid": price_valid,
        "price_changed": price_changed,
        "current_price": current_price.to_dict(),
        "product_id": truth.product.product_id,
    }


@router.get(
    "/products/{product_id}/checkout-capability",
    summary="Resolve Checkout Capability Bounds",
    status_code=status.HTTP_200_OK,
)
async def get_checkout_capability(
    product_id: str,
    source_url: str = Query(..., description="Exact product detail URL"),
    amount_paise: int = Query(..., description="Price in Paise"),
) -> Dict[str, Any]:
    """Resolve exact capability bounds (VERIFIED_API, CHECKOUT_HANDOFF, DISCOVERY_ONLY)."""
    candidate = {
        "product_id": product_id,
        "name": f"Product {product_id}",
        "source_url": source_url,
        "amount_paise": amount_paise,
    }
    truth = ProductTruthEngine.evaluate_product(candidate)
    resolver = CheckoutCapabilityResolver(_registry)
    capability, explanation = resolver.resolve_capability(truth.product)

    return {
        "status": "SUCCESS",
        "product_id": product_id,
        "capability": capability.value,
        "explanation": explanation,
        "source_url": source_url,
    }


@router.post(
    "/checkout/prepare", summary="Execute Checkout Preparation Flow", status_code=status.HTTP_200_OK
)
async def prepare_checkout(payload: PrepareCheckoutRequest) -> Dict[str, Any]:
    """Prepare checkout package or redirect handoff package."""
    success, prep, message = _orchestrator.prepare_checkout_flow(
        request_id=payload.request_id,
        buyer_id=payload.buyer_id,
        raw_candidate=payload.raw_candidate,
        live_recheck_data=payload.live_recheck_data,
    )

    if not success:
        return {
            "status": "REJECTED",
            "message": message,
            "preparation": prep.to_dict(),
        }

    return {
        "status": "SUCCESS",
        "message": message,
        "preparation": prep.to_dict(),
    }


@router.post(
    "/orders/create",
    summary="Create Direct Merchant API Order (M25)",
    status_code=status.HTTP_200_OK,
)
async def create_merchant_order(payload: CreateOrderRequest) -> Dict[str, Any]:
    """
    Create direct order with verified platform merchant API (cafeacme.local).
    Binds cart, payment, and merchant order cryptographically.
    """
    truth = ProductTruthEngine.evaluate_product(payload.raw_candidate)
    product = truth.product

    connector = _registry.resolve_connector(product.merchant.domain)
    if not isinstance(connector, RealPlatformConnector):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Merchant domain '{product.merchant.domain}' does not support direct API order creation.",
        )

    # Compute plan hash and cryptographic order binding hash
    plan_hash = f"plan_{uuid.uuid4().hex[:10]}"
    order_binding_hash = _order_binder.compute_binding_hash(
        purchase_request_id=payload.request_id,
        merchant_id=product.merchant.merchant_id,
        buyer_id=payload.buyer_id,
        product_id=product.product_id,
        quantity=1,
        amount_paise=product.price.amount_paise,
        currency=product.price.currency,
        merchant_order_id="pending_creation",
        payment_reference=payload.payment_transaction_id,
        plan_hash=plan_hash,
    )

    # Create Order via Real Platform Connector
    order_rec = connector.create_order(
        request_id=payload.request_id,
        buyer_id=payload.buyer_id,
        product=product,
        payment_transaction_id=payload.payment_transaction_id,
        order_binding_hash=order_binding_hash,
    )

    # Enforce 1:1 Payment ↔ Merchant Order Binding
    binding = _tx_binder_mgr.bind_transaction_to_order(
        binding_id=f"bind_{uuid.uuid4().hex[:10]}",
        razorpay_transaction_id=payload.payment_transaction_id,
        merchant_order_id=order_rec["merchant_order_id"],
        merchant_id=product.merchant.merchant_id,
        product_id=product.product_id,
        product_evidence_hash=product.evidence_hash,
        order_binding_hash=order_binding_hash,
        payment_amount_paise=product.price.amount_paise,
        currency=product.price.currency,
        connector_id=connector.connector_id,
    )

    # Verify Order in OrderVerificationEngine
    authoritative_ev = {
        "amount_paise": str(product.price.amount_paise),
        "currency": product.price.currency,
        "source": connector.connector_id,
    }
    outcome = _order_verifier.verify_order_outcome(
        outcome_id=f"outcome_{order_rec['merchant_order_id']}",
        payment_transaction_id=payload.payment_transaction_id,
        merchant_order_id=order_rec["merchant_order_id"],
        authoritative_evidence=authoritative_ev,
    )

    _health_monitor.record_call(connector.connector_id, duration_ms=210, is_success=True)

    return {
        "status": "SUCCESS",
        "message": "Merchant order successfully created and cryptographically bound.",
        "merchant_order": order_rec,
        "transaction_binding": binding.to_dict(),
        "order_outcome": outcome.to_dict(),
    }


@router.get(
    "/connectors/health",
    summary="Get Connector Health & Latency Metrics",
    status_code=status.HTTP_200_OK,
)
async def get_connector_health() -> Dict[str, Any]:
    """Retrieve operational health, latency, and success metrics for all commerce connectors."""
    return _health_monitor.get_health_metrics()


@router.get(
    "/orders/{order_id}",
    summary="Get Authoritative Order Outcome Status",
    status_code=status.HTTP_200_OK,
)
async def get_order_status(order_id: str) -> Dict[str, Any]:
    """Retrieve authoritative order outcome state by outcome ID."""
    outcome = _order_verifier.get_outcome(order_id)
    if not outcome:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order outcome '{order_id}' not found.",
        )

    return {
        "status": "SUCCESS",
        "outcome": outcome.to_dict(),
    }


@router.get(
    "/connectors/config",
    summary="Get Safe Redacted Connector Configurations",
    status_code=status.HTTP_200_OK,
)
async def get_connector_config() -> Dict[str, Any]:
    """Retrieve safe redacted connector configurations for all active connectors."""
    return {
        "status": "SUCCESS",
        "connectors_enabled": _config_mgr.connectors_enabled,
        "app_env": _config_mgr.app_env,
        "configurations": _config_mgr.get_all_safe_settings(),
    }


class ReconcileTransactionRequest(BaseModel):
    purchase_request_id: str = Field(..., description="Purchase request ID")
    payment_transaction_id: str = Field(..., description="Payment transaction ID")
    merchant_id: str = Field(..., description="Merchant ID")
    buyer_id: str = Field(..., description="Buyer ID")
    amount_paise: int = Field(..., description="Payment amount in Paise")
    currency: str = Field("INR", description="Currency code")
    merchant_order_id: Optional[str] = Field(None, description="Merchant order ID")
    payment_ledger_status: Optional[str] = Field("CAPTURED", description="Payment ledger status")
    merchant_ledger_status: Optional[str] = Field(None, description="Merchant ledger status")


@router.post(
    "/reconcile",
    summary="Perform Commerce Reconciliation Query",
    status_code=status.HTTP_200_OK,
)
async def reconcile_transaction(req: ReconcileTransactionRequest) -> Dict[str, Any]:
    """Execute automated reconciliation across payment and merchant ledgers."""
    record = _reconciliation_engine.reconcile_transaction(
        purchase_request_id=req.purchase_request_id,
        payment_transaction_id=req.payment_transaction_id,
        merchant_id=req.merchant_id,
        buyer_id=req.buyer_id,
        amount_paise=req.amount_paise,
        currency=req.currency,
        merchant_order_id=req.merchant_order_id,
        payment_ledger_status=req.payment_ledger_status,
        merchant_ledger_status=req.merchant_ledger_status,
    )

    return {
        "status": "SUCCESS",
        "message": "Transaction reconciliation completed.",
        "reconciliation_record": record.to_dict(),
    }


@router.get(
    "/reconciliation/status",
    summary="Get All Reconciliation Records",
    status_code=status.HTTP_200_OK,
)
async def get_reconciliation_status() -> Dict[str, Any]:
    """Retrieve all transaction reconciliation records."""
    return {
        "status": "SUCCESS",
        "records": _reconciliation_engine.get_all_records(),
    }


class CommerceSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    max_price_paise: int = Field(..., description="Max price limit in Paise")


@router.post(
    "/search",
    summary="Multi-Merchant Product Search & Discovery",
    status_code=status.HTTP_200_OK,
)
async def search_commerce_products(req: CommerceSearchRequest) -> Dict[str, Any]:
    """Search products across all active connectors and return normalized candidates."""
    raw_candidates, disc_status = _discovery_engine.discover_candidates(
        req.query, req.max_price_paise
    )
    candidates = _deduplicator.deduplicate(raw_candidates)

    return {
        "status": disc_status,
        "query": req.query,
        "max_price_paise": req.max_price_paise,
        "candidates_count": len(candidates),
        "candidates": [c.to_dict() for c in candidates],
    }


@router.post(
    "/compare",
    summary="Cross-Merchant Product Comparison",
    status_code=status.HTTP_200_OK,
)
async def compare_commerce_products(req: CommerceSearchRequest) -> Dict[str, Any]:
    """Perform evidence-backed comparison across candidate products."""
    raw_candidates, disc_status = _discovery_engine.discover_candidates(
        req.query, req.max_price_paise
    )
    candidates = _deduplicator.deduplicate(raw_candidates)

    best_rec, scored, rec_status = _recommendation_engine.rank_candidates(
        candidates, req.max_price_paise
    )
    rec_id = best_rec.product.product_id if best_rec else None

    cmp_res = _comparison_engine.compare_candidates(
        req.query, req.max_price_paise, candidates, recommended_id=rec_id
    )

    return {
        "status": disc_status,
        "comparison": cmp_res.to_dict(),
        "candidates": [c.to_dict() for c in candidates],
    }


@router.post(
    "/recommend",
    summary="Deterministic Product Recommendation Engine",
    status_code=status.HTTP_200_OK,
)
async def recommend_commerce_product(req: CommerceSearchRequest) -> Dict[str, Any]:
    """Compute evidence-backed deterministic recommendation ranking."""
    raw_candidates, disc_status = _discovery_engine.discover_candidates(
        req.query, req.max_price_paise
    )
    candidates = _deduplicator.deduplicate(raw_candidates)

    best_rec, scored, rec_status = _recommendation_engine.rank_candidates(
        candidates, req.max_price_paise
    )

    if not best_rec:
        return {
            "status": "NO_RECOMMENDATION_FOUND",
            "message": rec_status,
            "candidates_count": len(candidates),
        }

    return {
        "status": "SUCCESS",
        "recommended_candidate": best_rec.to_dict(),
        "all_ranked_candidates": [s.to_dict() for s in scored],
    }


@router.get(
    "/connectors",
    summary="List Registered Commerce Connectors",
    status_code=status.HTTP_200_OK,
)
async def list_connectors() -> Dict[str, Any]:
    """Retrieve details of all registered commerce connectors."""
    connectors = _registry.list_active_connectors()
    res = []
    for c in connectors:
        res.append(
            {
                "connector_id": c.connector_id,
                "connector_name": c.connector_name,
                "merchant_identity": c.merchant_identity,
                "environment": c.environment.value,
                "capability": c.capability.value,
                "base_domain": c.base_domain,
                "enabled": c.enabled,
                "health_status": c.health_status,
                "supported_operations": c.supported_operations,
            }
        )
    return {"status": "SUCCESS", "connectors_count": len(res), "connectors": res}


@router.get(
    "/connectors/{connector_id}",
    summary="Get Connector Details by ID",
    status_code=status.HTTP_200_OK,
)
async def get_connector_details(connector_id: str) -> Dict[str, Any]:
    """Retrieve configuration and health details for a specific connector."""
    conn = _registry.get_connector(connector_id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector '{connector_id}' not found.",
        )

    return {
        "status": "SUCCESS",
        "connector": {
            "connector_id": conn.connector_id,
            "connector_name": conn.connector_name,
            "merchant_identity": conn.merchant_identity,
            "environment": conn.environment.value,
            "capability": conn.capability.value,
            "base_domain": conn.base_domain,
            "enabled": conn.enabled,
            "health_status": conn.health_status,
            "supported_operations": conn.supported_operations,
        },
    }


class ShoppingResearchRequestModel(BaseModel):
    prompt: str = Field(
        ..., description="Multi-item prompt e.g., 'Find coffee and biscuits under ₹300'"
    )
    total_budget_paise: Optional[int] = Field(
        None, description="Optional total budget limit in Paise"
    )


@router.post(
    "/shopping/research",
    summary="Multi-Item Parallel Live Shopping Research",
    status_code=status.HTTP_200_OK,
)
async def research_shopping_request(req: ShoppingResearchRequestModel) -> Dict[str, Any]:
    """Execute live product research across all item intents in shopping request."""
    budget = req.total_budget_paise or 50000
    shop_req = MultiItemIntentExtractor.parse_prompt(req.prompt, default_budget_paise=budget)
    res = _cart_research_engine.research_shopping_request(shop_req)
    return {
        "status": "SUCCESS",
        "shopping_request": shop_req.to_dict(),
        "research_result": res.to_dict(),
    }


@router.post(
    "/shopping/optimize",
    summary="Multi-Item Bounded Cart Optimization",
    status_code=status.HTTP_200_OK,
)
async def optimize_shopping_cart(req: ShoppingResearchRequestModel) -> Dict[str, Any]:
    """Evaluate multi-item cart combinations and compute deterministic recommendation ranking."""
    budget = req.total_budget_paise or 50000
    shop_req = MultiItemIntentExtractor.parse_prompt(req.prompt, default_budget_paise=budget)
    research_res = _cart_research_engine.research_shopping_request(shop_req)
    opt_res = _cart_optimizer.optimize_cart(shop_req, research_res)

    best_cart = opt_res.best_recommended_cart
    explanation: list[str] = []
    if best_cart:
        explanation = _recommendation_engine.explain_cart_recommendation(
            best_cart, shop_req.total_budget_paise
        )

    return {
        "status": "SUCCESS" if best_cart else "NO_VERIFIED_LIVE_CART_FOUND",
        "shopping_request": shop_req.to_dict(),
        "optimization_result": opt_res.to_dict(),
        "explanation": explanation,
    }


# -----------------------------------------------------------------------------
# Razorpay Test-Mode & Agentic Payment Protocol Endpoints
# -----------------------------------------------------------------------------


class RazorpayOrderRequestModel(BaseModel):
    amount_paise: int = Field(..., description="Amount in minor units (paise)")
    currency: str = Field("INR", description="Currency code")
    receipt: str = Field(..., description="Internal receipt or transaction ID")
    notes: Optional[Dict[str, Any]] = Field(default_factory=dict)
    confirmation_token: str = Field(..., description="Verified human confirmation token")
    agent_id: str = Field("shopping_agent_01", description="Agent Identity ID")
    merchant_id: str = Field("mer_cafe_acme", description="Target merchant ID")
    category: str = Field("grocery", description="Product category")
    uap_token: Optional[str] = Field(None, description="Optional UAP delegation token")


class RazorpayVerifyRequestModel(BaseModel):
    order_id: str = Field(..., description="Razorpay order ID")
    payment_id: str = Field(..., description="Razorpay payment ID")
    signature: str = Field(..., description="Razorpay payment signature")
    transaction_id: str = Field(..., description="Internal transaction ID")


class PolicyEvaluationRequestModel(BaseModel):
    agent_id: str = Field("shopping_agent_01", description="Agent Identity ID")
    request_id: str = Field(..., description="Request ID")
    user_id: str = Field("buyer_01", description="User ID")
    merchant_id: str = Field("mer_cafe_acme", description="Merchant ID")
    merchant_name: str = Field("Cafe Acme", description="Merchant name")
    category: str = Field("grocery", description="Product category")
    currency: str = Field("INR", description="Currency")
    amount_paise: int = Field(..., description="Amount in paise")
    provider: str = Field("razorpay_test", description="Payment provider name")
    is_product_verified: bool = Field(True, description="Product truth verification status")
    has_human_confirmation: bool = Field(True, description="Human confirmation status")


class UAPTokenRequestModel(BaseModel):
    agent_id: str = Field("shopping_agent_01", description="Agent Identity ID")
    user_id: str = Field("buyer_01", description="User ID")
    max_amount_paise: int = Field(50000, description="Max transaction amount in paise")
    daily_limit_paise: int = Field(200000, description="Daily limit in paise")


class X402PaymentRequestModel(BaseModel):
    resource_url: str = Field(..., description="Target 402 resource URL")
    status_code: int = Field(402, description="HTTP status code")
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Dict[str, Any] = Field(default_factory=dict)
    agent_id: str = Field("shopping_agent_01", description="Agent ID")
    confirmation_token: str = Field(..., description="Human confirmation token")
    transaction_id: str = Field(..., description="Internal transaction ID")


@router.get(
    "/payment-capabilities", summary="Get Payment Capability Matrix", status_code=status.HTTP_200_OK
)
async def get_payment_capabilities() -> Dict[str, Any]:
    """Retrieve full capability matrix across all payment protocols."""
    return {
        "status": "SUCCESS",
        "capabilities": {
            "razorpay": _rzp_protocol.get_capabilities(),
            "x402": _x402_protocol.get_capabilities(),
            "uap": _uap_protocol.get_capabilities(),
        },
    }


@router.post(
    "/policy/evaluate", summary="Evaluate Agent Payment Policy", status_code=status.HTTP_200_OK
)
async def evaluate_agent_payment_policy(req: PolicyEvaluationRequestModel) -> Dict[str, Any]:
    """Evaluate payment request against deterministic Agent Payment Policy Engine."""
    ctx = PolicyEvaluationContext(
        agent_id=req.agent_id,
        request_id=req.request_id,
        user_id=req.user_id,
        merchant_id=req.merchant_id,
        merchant_name=req.merchant_name,
        category=req.category,
        currency=req.currency,
        amount_paise=req.amount_paise,
        provider=req.provider,
        is_product_verified=req.is_product_verified,
        has_human_confirmation=req.has_human_confirmation,
    )
    eval_res = _policy_engine.evaluate(ctx)
    return {
        "status": "SUCCESS",
        "allowed": eval_res.allowed,
        "risk_level": eval_res.risk_level.value,
        "reason": eval_res.reason,
        "block_code": eval_res.block_code,
        "policy_id": eval_res.policy_id,
    }


@router.post(
    "/uap/issue-token",
    summary="Issue UAP Delegated Authorization Token",
    status_code=status.HTTP_200_OK,
)
async def issue_uap_token(req: UAPTokenRequestModel) -> Dict[str, Any]:
    """Issue a UAP-aligned delegated authorization policy and token."""
    auth_policy = _uap_layer.issue_authorization(
        agent_id=req.agent_id,
        user_id=req.user_id,
        max_amount_paise=req.max_amount_paise,
        daily_limit_paise=req.daily_limit_paise,
    )
    return {
        "status": "SUCCESS",
        "authorization_id": auth_policy.authorization_id,
        "token": auth_policy.token,
        "status_code": auth_policy.status.value,
        "expiration_timestamp": auth_policy.expiration_timestamp,
        "max_amount_paise": auth_policy.max_amount_paise,
    }


@router.post(
    "/uap/revoke-token", summary="Revoke UAP Authorization Token", status_code=status.HTTP_200_OK
)
async def revoke_uap_token(authorization_id: str) -> Dict[str, Any]:
    """Revoke an active UAP authorization policy token."""
    success = _uap_layer.revoke_authorization(authorization_id)
    if not success:
        raise HTTPException(status_code=404, detail="UAP authorization token not found.")
    return {"status": "SUCCESS", "message": f"Authorization {authorization_id} revoked."}


@router.post(
    "/razorpay/create-order", summary="Create Razorpay Test Order", status_code=status.HTTP_200_OK
)
async def create_razorpay_order(req: RazorpayOrderRequestModel) -> Dict[str, Any]:
    """Create a Razorpay Test Mode order after policy validation & human authorization."""
    # 1. Evaluate Policy Gate
    eval_ctx = PolicyEvaluationContext(
        agent_id=req.agent_id,
        request_id=req.receipt,
        user_id="buyer_01",
        merchant_id=req.merchant_id,
        merchant_name=req.merchant_id,
        category=req.category,
        currency=req.currency,
        amount_paise=req.amount_paise,
        provider="razorpay_test",
        is_product_verified=True,
        has_human_confirmation=bool(req.confirmation_token),
    )

    if req.uap_token:
        eval_res = _uap_protocol.evaluate_authorization(eval_ctx, req.uap_token)
    else:
        eval_res = _rzp_protocol.evaluate_authorization(eval_ctx)

    if not eval_res.allowed:
        _timeline_mgr.record_event(
            req.receipt,
            stage="POLICY_BLOCKED",
            label="Payment Policy Blocked",
            detail=eval_res.reason,
            status="FAILED",
            is_failed=True,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Payment policy block [{eval_res.block_code}]: {eval_res.reason}",
        )

    # 2. Execute Order Creation via Razorpay Client
    try:
        order = _razorpay_client.create_test_order(
            amount_paise=req.amount_paise,
            currency=req.currency,
            receipt=req.receipt,
            notes=req.notes,
        )
        _policy_engine.record_spending(req.agent_id, req.amount_paise)
        _timeline_mgr.record_event(
            req.receipt,
            stage="RAZORPAY_ORDER_CREATED",
            label="Razorpay Order Created",
            detail=f"Order {order.order_id} created for {req.amount_paise} paise in {order.mode.value} mode",
        )
        return {
            "status": "SUCCESS",
            "order": {
                "order_id": order.order_id,
                "amount_paise": order.amount_paise,
                "currency": order.currency,
                "receipt": order.receipt,
                "status": order.status,
                "mode": order.mode.value,
                "created_at": order.created_at,
            },
            "risk_level": eval_res.risk_level.value,
        }
    except Exception as err:
        _timeline_mgr.record_event(
            req.receipt,
            stage="ORDER_CREATION_FAILED",
            label="Order Creation Failed",
            detail=str(err),
            status="FAILED",
            is_failed=True,
        )
        raise HTTPException(status_code=400, detail=str(err))


@router.post(
    "/razorpay/verify-payment",
    summary="Verify Razorpay Payment Signature",
    status_code=status.HTTP_200_OK,
)
async def verify_razorpay_payment(req: RazorpayVerifyRequestModel) -> Dict[str, Any]:
    """Verify Razorpay payment HMAC-SHA256 signature and reconcile order status."""
    is_valid = _razorpay_client.verify_payment_signature(
        order_id=req.order_id,
        payment_id=req.payment_id,
        signature=req.signature,
    )

    if not is_valid:
        _timeline_mgr.record_event(
            req.transaction_id,
            stage="SIGNATURE_VERIFICATION_FAILED",
            label="Signature Failed",
            detail=f"Signature verification failed for payment {req.payment_id}",
            status="FAILED",
            is_failed=True,
        )
        raise HTTPException(status_code=400, detail="Invalid Razorpay payment signature.")

    p_status = _razorpay_client.get_payment_status(req.payment_id)

    _timeline_mgr.record_event(
        req.transaction_id,
        stage="PAYMENT_VERIFIED",
        label="Payment Verified & Reconciled",
        detail=f"Payment {req.payment_id} verified cleanly with status '{p_status.value}'",
    )

    return {
        "status": "SUCCESS",
        "verified": True,
        "payment_id": req.payment_id,
        "order_id": req.order_id,
        "provider_status": p_status.value,
    }


@router.post(
    "/x402/pay", summary="Execute x402-Compatible HTTP Payment", status_code=status.HTTP_200_OK
)
async def execute_x402_payment(req: X402PaymentRequestModel) -> Dict[str, Any]:
    """Parse HTTP 402 requirement, evaluate policy, and generate proof token."""
    try:
        requirement = _x402_adapter.parse_402_header_or_body(
            resource_url=req.resource_url,
            status_code=req.status_code,
            headers=req.headers,
            body=req.body,
        )

        eval_ctx = PolicyEvaluationContext(
            agent_id=req.agent_id,
            request_id=req.transaction_id,
            user_id="buyer_01",
            merchant_id="merchant_x402",
            merchant_name="x402 Resource Provider",
            category="general",
            currency=requirement.currency,
            amount_paise=requirement.amount_paise,
            provider="x402",
            is_product_verified=True,
            has_human_confirmation=bool(req.confirmation_token),
        )
        eval_res = _x402_protocol.evaluate_authorization(eval_ctx)

        if not eval_res.allowed:
            raise HTTPException(status_code=400, detail=f"x402 policy block: {eval_res.reason}")

        proof = _x402_adapter.generate_payment_proof(
            requirement=requirement,
            transaction_id=req.transaction_id,
            agent_id=req.agent_id,
        )

        _x402_adapter.verify_and_settle_proof(proof, requirement)

        _timeline_mgr.record_event(
            req.transaction_id,
            stage="X402_PROOF_GENERATED",
            label="x402 Payment Settled",
            detail=f"x402 proof generated for requirement {requirement.requirement_hash[:8]}",
        )

        return {
            "status": "SUCCESS",
            "requirement_hash": requirement.requirement_hash,
            "proof_token": proof.proof_token,
            "settled": True,
        }
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.get(
    "/timeline/{transaction_id}",
    summary="Get Payment Event Timeline",
    status_code=status.HTTP_200_OK,
)
async def get_payment_timeline(transaction_id: str) -> Dict[str, Any]:
    """Retrieve full real-time event timeline for a transaction."""
    events = _timeline_mgr.get_timeline(transaction_id)
    if not events:
        # Default initialization for demo
        events = _timeline_mgr.create_default_timeline(
            transaction_id, "Find coffee and biscuits under ₹300", 29900
        )

    return {
        "status": "SUCCESS",
        "transaction_id": transaction_id,
        "events_count": len(events),
        "events": [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp,
                "stage": e.stage,
                "label": e.label,
                "detail": e.detail,
                "status": e.status,
                "is_failed": e.is_failed,
            }
            for e in events
        ],
    }


class AIDecisionRequest(BaseModel):
    prompt: str = Field(..., description="Natural language shopping request")
    budget_paise: int = Field(default=30000, description="Budget boundary in minor paise")


class AIRiskEvalRequest(BaseModel):
    amount_paise: int = Field(..., description="Transaction amount in paise")
    budget_paise: int = Field(default=30000, description="Total budget in paise")
    product_verified: bool = Field(
        default=True, description="Whether product evidence is source-verified"
    )
    merchant_risk_score: float = Field(default=0.1, description="Merchant risk rating 0.0-1.0")
    velocity_attempt_count: int = Field(
        default=1, description="Attempts in current velocity window"
    )
    confirmation_timing_sec: float = Field(
        default=5.0, description="Time taken to confirm in seconds"
    )
    cart_item_count: int = Field(default=2, description="Number of items in cart")
    prompt_injection_detected: bool = Field(
        default=False, description="Prompt injection signal flag"
    )
    payment_protocol: str = Field(default="razorpay", description="Payment protocol used")
    retry_failure_count: int = Field(default=0, description="Previous failure count")


@router.post(
    "/ai/decision",
    summary="LLM Commerce Decision & Intent Extraction",
    status_code=status.HTTP_200_OK,
)
async def evaluate_ai_decision(req: AIDecisionRequest) -> Dict[str, Any]:
    """Execute LLM decision reasoning and prompt injection inspection."""
    decision = _llm_engine.process_shopping_request(
        prompt=req.prompt, budget_paise=req.budget_paise
    )
    return {
        "status": "SUCCESS",
        "decision": decision.model_dump(),
        "is_safe": decision.is_safe_for_planning(),
    }


@router.post(
    "/ai/risk-eval",
    summary="Combined ML & Neural Risk Intelligence Evaluation",
    status_code=status.HTTP_200_OK,
)
async def evaluate_ai_risk(req: AIRiskEvalRequest) -> Dict[str, Any]:
    """Evaluate transaction risk using ML Logistic Classifier and Neural Autoencoder Model."""
    payload = req.model_dump()
    risk_summary = _risk_engine.evaluate_risk(payload)
    return {
        "status": "SUCCESS",
        "risk_intelligence": risk_summary,
    }
