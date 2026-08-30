"""
Mandate Gateway — Commerce API Router (M24)
Workstream 14 — Production REST API endpoints for product truth verification,
price revalidation, capability resolution, checkout preparation, and order status.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from apps.api.commerce.checkout_orchestrator import CheckoutOrchestrator
from apps.api.commerce.connector_registry import CommerceConnectorRegistry
from apps.api.commerce.connector_resolver import CheckoutCapabilityResolver
from apps.api.commerce.models import ProductVerificationStatus
from apps.api.commerce.order_verification import OrderVerificationEngine
from apps.api.commerce.price_revalidation import LivePriceRevalidator
from apps.api.commerce.product_truth_engine import ProductTruthEngine

router = APIRouter(prefix="/api/v1/commerce", tags=["Commerce Truth & Checkout"])

_registry = CommerceConnectorRegistry()
_orchestrator = CheckoutOrchestrator(registry=_registry)
_order_verifier = OrderVerificationEngine()


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


@router.get(
    "/orders/{order_id}",
    summary="Get Authoritative Order Outcome Status",
    status_code=status.HTTP_200_OK,
)
async def get_order_status(order_id: str) -> Dict[str, Any]:
    """Retrieve authoritative order outcome state by outcome ID."""
    outcome = _orchestrator.order_verifier.get_outcome(order_id)
    if not outcome:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order outcome '{order_id}' not found.",
        )

    return {
        "status": "SUCCESS",
        "outcome": outcome.to_dict(),
    }
