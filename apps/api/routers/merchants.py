"""
S03.1 — Merchant & Merchant Policy API Router.

Implements REST API endpoints for merchant management and merchant policy updates (Section 28, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable
import uuid

from apps.api.contracts.merchant import (
    MerchantCreate,
    MerchantResponse,
    PolicyCreate,
    PolicyResponse,
)
from apps.api.domain.types import Currency, McpOperation, Region

try:
    from fastapi import APIRouter, HTTPException, status

    HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    HAS_FASTAPI = False
    APIRouter = Any

    class status:  # type: ignore[no-redef]
        HTTP_200_OK = 200
        HTTP_201_CREATED = 201
        HTTP_404_NOT_FOUND = 404
        HTTP_400_BAD_REQUEST = 400

    class HTTPException(Exception):  # type: ignore[no-redef]
        def __init__(self, status_code: int, detail: str) -> None:
            self.status_code = status_code
            self.detail = detail


# In-memory store for merchants & merchant policies
_MERCHANTS: dict[str, MerchantResponse] = {}
_MERCHANT_POLICIES: dict[str, PolicyResponse] = {}


if HAS_FASTAPI:
    merchants_router = APIRouter(prefix="/api", tags=["Merchant & Policy Management"])
else:

    class DummyRouter:
        def post(self, *args: Any, **kwargs: Any) -> Callable:
            def decorator(func: Callable) -> Callable:
                return func

            return decorator

        def get(self, *args: Any, **kwargs: Any) -> Callable:
            def decorator(func: Callable) -> Callable:
                return func

            return decorator

        def put(self, *args: Any, **kwargs: Any) -> Callable:
            def decorator(func: Callable) -> Callable:
                return func

            return decorator

    merchants_router = DummyRouter()


@merchants_router.post(
    "/merchants",
    response_model=MerchantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_merchant(payload: MerchantCreate) -> MerchantResponse:
    """Register a new merchant."""
    merchant_id = f"mer_{uuid.uuid4().hex[:12]}"
    merchant = MerchantResponse(
        merchant_id=merchant_id,
        name=payload.name,
        razorpay_account_id=payload.razorpay_account_id,
        created_at=datetime.now(timezone.utc),
    )
    _MERCHANTS[merchant_id] = merchant

    # Initialize default policy for new merchant
    default_policy = PolicyResponse(
        policy_id=f"pol_{uuid.uuid4().hex[:12]}",
        merchant_id=merchant_id,
        policy_version=1,
        ai_commerce_enabled=True,
        currency=Currency.INR,
        allowed_categories=frozenset(["electronics", "clothing", "books", "supplies"]),
        autonomous_purchase_limit_paise=500000,  # ₹5,000
        step_up_threshold_paise=1000000,  # ₹10,000
        max_step_up_percent=10,
        allowed_regions=frozenset([Region.IN]),
        allowed_operations=frozenset([McpOperation.CREATE_ORDER, McpOperation.FETCH_PAYMENT]),
        blocked_operations=frozenset([McpOperation.PAYOUT, McpOperation.BANK_TRANSFER]),
        created_at=datetime.now(timezone.utc),
        expires_at=None,
    )
    _MERCHANT_POLICIES[merchant_id] = default_policy

    return merchant


@merchants_router.get(
    "/merchants/{merchant_id}",
    response_model=MerchantResponse,
)
def get_merchant(merchant_id: str) -> MerchantResponse:
    """Fetch merchant by ID."""
    if merchant_id not in _MERCHANTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant '{merchant_id}' not found.",
        )
    return _MERCHANTS[merchant_id]


@merchants_router.post(
    "/merchants/{merchant_id}/policy",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
@merchants_router.put(
    "/merchants/{merchant_id}/policy",
    response_model=PolicyResponse,
)
def update_merchant_policy(merchant_id: str, payload: PolicyCreate) -> PolicyResponse:
    """Create or update merchant policy."""
    if merchant_id not in _MERCHANTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant '{merchant_id}' not found.",
        )

    current_policy = _MERCHANT_POLICIES.get(merchant_id)
    policy_version = (current_policy.policy_version + 1) if current_policy else 1

    updated_policy = PolicyResponse(
        policy_id=current_policy.policy_id if current_policy else f"pol_{uuid.uuid4().hex[:12]}",
        merchant_id=merchant_id,
        policy_version=policy_version,
        ai_commerce_enabled=payload.ai_commerce_enabled,
        currency=payload.currency,
        allowed_categories=frozenset([cat.lower() for cat in payload.allowed_categories]),
        autonomous_purchase_limit_paise=payload.autonomous_purchase_limit_paise,
        step_up_threshold_paise=payload.step_up_threshold_paise,
        max_step_up_percent=payload.max_step_up_percent,
        allowed_regions=frozenset(payload.allowed_regions),
        allowed_operations=frozenset(payload.allowed_operations),
        blocked_operations=frozenset(payload.blocked_operations),
        created_at=datetime.now(timezone.utc),
        expires_at=payload.expires_at,
    )
    _MERCHANT_POLICIES[merchant_id] = updated_policy
    return updated_policy


@merchants_router.get(
    "/merchants/{merchant_id}/policy",
    response_model=PolicyResponse,
)
def get_merchant_policy(merchant_id: str) -> PolicyResponse:
    """Fetch active policy for merchant."""
    if merchant_id not in _MERCHANTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant '{merchant_id}' not found.",
        )
    if merchant_id not in _MERCHANT_POLICIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy for merchant '{merchant_id}' not found.",
        )
    return _MERCHANT_POLICIES[merchant_id]
