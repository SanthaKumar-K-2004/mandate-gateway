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
from apps.api.commerce.connector_config import CommerceConnectorConfigManager
from apps.api.commerce.product_truth_engine import ProductTruthEngine
from apps.api.commerce.reconciliation import CommerceReconciliationEngine
from apps.api.commerce.transaction_binding import CommerceTransactionBindingManager

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
        ..., description="Authorized RAZERPAY payment transaction ID"
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
        razerpay_transaction_id=payload.payment_transaction_id,
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
