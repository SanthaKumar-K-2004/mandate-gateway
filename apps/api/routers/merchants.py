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
    APIRouter = Any  # type: ignore[misc,assignment]

    class status:  # type: ignore[no-redef]
        HTTP_200_OK = 200
        HTTP_201_CREATED = 201
        HTTP_404_NOT_FOUND = 404
        HTTP_400_BAD_REQUEST = 400

    class HTTPException(Exception):  # type: ignore[no-redef]
        def __init__(self, status_code: int, detail: str) -> None:
            self.status_code = status_code
            self.detail = detail


import json
from db.unit_of_work import AsyncUnitOfWork

# In-memory fallback store for merchants & merchant policies
_MERCHANTS: dict[str, MerchantResponse] = {}
_MERCHANT_POLICIES: dict[str, PolicyResponse] = {}


def _get_uow_or_none() -> AsyncUnitOfWork | None:
    """Return an active AsyncUnitOfWork if the database session factory is initialized."""
    from db.session import _async_session_factory

    if _async_session_factory is not None:
        return AsyncUnitOfWork()
    return None


if HAS_FASTAPI:
    merchants_router: Any = APIRouter(prefix="/api", tags=["Merchant & Policy Management"])
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

    merchants_router: Any = DummyRouter()  # type: ignore[no-redef]


@merchants_router.post(
    "/merchants",
    response_model=MerchantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_merchant(payload: MerchantCreate) -> MerchantResponse:
    """Register a new merchant in database and memory."""
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

    # Persist to database if database session factory is available
    uow = _get_uow_or_none()
    if uow is not None:
        import asyncio

        async def _persist() -> None:
            async with uow:
                await uow.merchants.create_merchant(
                    merchant_id=merchant_id,
                    name=payload.name,
                    razorpay_account_id=payload.razorpay_account_id,
                )
                await uow.merchants.create_policy(
                    policy_id=default_policy.policy_id,
                    merchant_id=merchant_id,
                    policy_version="1",
                    active=True,
                    autonomous_limit_paise=500000,
                    step_up_threshold_paise=1000000,
                    allowed_categories=list(default_policy.allowed_categories),
                    allowed_operations=[op.value for op in default_policy.allowed_operations],
                    blocked_operations=[op.value for op in default_policy.blocked_operations],
                )
                await uow.commit()

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_persist())
        except RuntimeError:
            asyncio.run(_persist())

    return merchant


@merchants_router.get(
    "/merchants/{merchant_id}",
    response_model=MerchantResponse,
)
def get_merchant(merchant_id: str) -> MerchantResponse:
    """Fetch merchant by ID."""
    uow = _get_uow_or_none()
    if uow is not None:
        import asyncio

        async def _get() -> MerchantResponse | None:
            async with uow:
                model = await uow.merchants.get_by_id(merchant_id)
                if model is not None:
                    return MerchantResponse(
                        merchant_id=model.merchant_id,
                        name=model.name,
                        razorpay_account_id=model.razorpay_account_id or "",
                        created_at=model.created_at,
                    )
                return None
            return None

        try:
            res = asyncio.run(_get())
            if res is not None:
                return res
        except Exception:
            pass

    if merchant_id not in _MERCHANTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant '{merchant_id}' not found.",
        )
    return _MERCHANTS[merchant_id]


@merchants_router.post(
    "/merchants/{merchant_id}/policy",
    response_model=PolicyResponse,
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
        allowed_categories=frozenset(payload.allowed_categories),
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

    uow = _get_uow_or_none()
    if uow is not None:
        import asyncio

        async def _persist_policy() -> None:
            async with uow:
                await uow.merchants.create_policy(
                    policy_id=updated_policy.policy_id,
                    merchant_id=merchant_id,
                    policy_version=str(policy_version),
                    active=payload.ai_commerce_enabled,
                    autonomous_limit_paise=payload.autonomous_purchase_limit_paise,
                    step_up_threshold_paise=payload.step_up_threshold_paise,
                    allowed_categories=list(payload.allowed_categories),
                    allowed_operations=[op.value for op in payload.allowed_operations],
                    blocked_operations=[op.value for op in payload.blocked_operations],
                )
                await uow.commit()

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_persist_policy())
        except RuntimeError:
            asyncio.run(_persist_policy())

    return updated_policy


@merchants_router.get(
    "/merchants/{merchant_id}/policy",
    response_model=PolicyResponse,
)
def get_merchant_policy(merchant_id: str) -> PolicyResponse:
    """Fetch active policy for merchant."""
    uow = _get_uow_or_none()
    if uow is not None:
        import asyncio

        async def _get_policy() -> PolicyResponse | None:
            async with uow:
                model = await uow.merchants.get_active_policy(merchant_id)
                if model is not None:
                    allowed_cats = json.loads(model.allowed_categories_json or "[]")
                    allowed_ops = json.loads(model.allowed_operations_json or "[]")
                    blocked_ops = json.loads(model.blocked_operations_json or "[]")
                    ver_int = int(model.policy_version) if model.policy_version.isdigit() else 1
                    return PolicyResponse(
                        policy_id=model.id,
                        merchant_id=model.merchant_id,
                        policy_version=ver_int,
                        ai_commerce_enabled=model.active,
                        currency=Currency.INR,
                        allowed_categories=frozenset(allowed_cats),
                        autonomous_purchase_limit_paise=model.autonomous_limit_paise,
                        step_up_threshold_paise=model.step_up_threshold_paise,
                        max_step_up_percent=10,
                        allowed_regions=frozenset([Region.IN]),
                        allowed_operations=frozenset([McpOperation(op) for op in allowed_ops]),
                        blocked_operations=frozenset([McpOperation(op) for op in blocked_ops]),
                        created_at=model.created_at,
                        expires_at=None,
                    )
                return None
            return None

        try:
            res = asyncio.run(_get_policy())
            if res is not None:
                return res
        except Exception:
            pass

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
