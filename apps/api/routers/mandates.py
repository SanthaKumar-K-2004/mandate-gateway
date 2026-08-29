"""
S03.1 — Buyer Mandate API Router.

Implements REST API endpoints for mandate issuance, fetching, and revocation (Section 28, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable
import uuid

from apps.api.contracts.mandate import (
    MandateCreate,
    MandateResponse,
    MandateRevokeResponse,
)
from apps.api.domain.types import MandateStatus

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


from db.unit_of_work import AsyncUnitOfWork

# In-memory fallback store for mandates
_MANDATES: dict[str, MandateResponse] = {}


def _get_uow_or_none() -> AsyncUnitOfWork | None:
    """Return an active AsyncUnitOfWork if the database session factory is initialized."""
    from db.session import _async_session_factory

    if _async_session_factory is not None:
        return AsyncUnitOfWork()
    return None


if HAS_FASTAPI:
    mandates_router: Any = APIRouter(prefix="/api", tags=["Buyer Mandate Management"])
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

    mandates_router: Any = DummyRouter()  # type: ignore[no-redef]


@mandates_router.post(
    "/mandates",
    response_model=MandateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_mandate(payload: MandateCreate) -> MandateResponse:
    """Issue a new buyer mandate in database and memory."""
    mandate_id = f"man_{uuid.uuid4().hex[:12]}"
    mandate = MandateResponse(
        mandate_id=mandate_id,
        buyer_id=payload.buyer_id,
        version=1,
        merchant_scope=frozenset(payload.merchant_scope),
        category_scope=frozenset([c.lower() for c in payload.category_scope]),
        allowed_regions=frozenset(payload.allowed_regions),
        maximum_amount_paise=payload.maximum_amount_paise,
        daily_budget_paise=payload.daily_budget_paise,
        currency=payload.currency,
        autonomous_execution=payload.autonomous_execution,
        status=MandateStatus.ACTIVE,
        issued_at=datetime.now(timezone.utc),
        expires_at=payload.expires_at,
    )
    _MANDATES[mandate_id] = mandate

    uow = _get_uow_or_none()
    if uow is not None:
        import asyncio

        async def _persist_mandate() -> None:
            async with uow:
                merchant_id_str = (
                    list(payload.merchant_scope)[0] if payload.merchant_scope else None
                )
                cat_scope_str = list(payload.category_scope)[0] if payload.category_scope else None
                await uow.mandates.create_mandate(
                    mandate_id=mandate_id,
                    buyer_id=payload.buyer_id,
                    daily_budget_paise=payload.daily_budget_paise,
                    expires_at=payload.expires_at,
                    merchant_id=merchant_id_str,
                    category_scope=cat_scope_str,
                    status=MandateStatus.ACTIVE,
                )
                await uow.commit()

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_persist_mandate())
        except RuntimeError:
            asyncio.run(_persist_mandate())

    return mandate


@mandates_router.get(
    "/mandates/{mandate_id}",
    response_model=MandateResponse,
)
def get_mandate(mandate_id: str) -> MandateResponse:
    """Fetch mandate by ID."""
    uow = _get_uow_or_none()
    if uow is not None:
        import asyncio

        async def _get_mandate_db() -> MandateResponse | None:
            async with uow:
                model = await uow.mandates.get_mandate(mandate_id)
                if model is not None:
                    from apps.api.domain.types import Currency, Region

                    merchant_scope = (
                        frozenset([model.merchant_id]) if model.merchant_id else frozenset()
                    )
                    category_scope = (
                        frozenset([model.category_scope]) if model.category_scope else frozenset()
                    )
                    return MandateResponse(
                        mandate_id=model.mandate_id,
                        buyer_id=model.buyer_id,
                        version=1,
                        merchant_scope=merchant_scope,
                        category_scope=category_scope,
                        allowed_regions=frozenset([Region.IN]),
                        maximum_amount_paise=model.daily_budget_paise,
                        daily_budget_paise=model.daily_budget_paise,
                        currency=Currency.INR,
                        autonomous_execution=True,
                        status=MandateStatus(model.status),
                        issued_at=model.created_at,
                        expires_at=model.expires_at,
                    )
                return None
            return None

        try:
            res = asyncio.run(_get_mandate_db())
            if res is not None:
                return res
        except Exception:
            pass

    if mandate_id not in _MANDATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mandate '{mandate_id}' not found.",
        )
    return _MANDATES[mandate_id]


@mandates_router.post(
    "/mandates/{mandate_id}/revoke",
    response_model=MandateRevokeResponse,
)
def revoke_mandate(mandate_id: str) -> MandateRevokeResponse:
    """Revoke an active mandate."""
    if mandate_id not in _MANDATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mandate '{mandate_id}' not found.",
        )

    current_mandate = _MANDATES[mandate_id]
    revoked_at = datetime.now(timezone.utc)

    # Update in-memory status
    updated_mandate = MandateResponse(
        mandate_id=current_mandate.mandate_id,
        buyer_id=current_mandate.buyer_id,
        version=current_mandate.version + 1,
        merchant_scope=current_mandate.merchant_scope,
        category_scope=current_mandate.category_scope,
        allowed_regions=current_mandate.allowed_regions,
        maximum_amount_paise=current_mandate.maximum_amount_paise,
        daily_budget_paise=current_mandate.daily_budget_paise,
        currency=current_mandate.currency,
        autonomous_execution=current_mandate.autonomous_execution,
        status=MandateStatus.REVOKED,
        issued_at=current_mandate.issued_at,
        expires_at=current_mandate.expires_at,
    )
    _MANDATES[mandate_id] = updated_mandate

    uow = _get_uow_or_none()
    if uow is not None:
        import asyncio

        async def _revoke_db() -> None:
            async with uow:
                await uow.mandates.transition_mandate_status(mandate_id, MandateStatus.REVOKED)
                await uow.commit()

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_revoke_db())
        except RuntimeError:
            asyncio.run(_revoke_db())

    return MandateRevokeResponse(
        mandate_id=mandate_id,
        status=MandateStatus.REVOKED,
        revoked_at=revoked_at,
    )
