"""
S06.5 — Webhook Processing REST API Router.

Exposes REST endpoint POST /api/webhooks/razorpay for external provider webhook events.
Implements raw HTTP body reading, signature header extraction, and WebhookEngine delegation.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from apps.api.domain.types import RejectionReason
from apps.api.domain.webhook_engine import WebhookEngine, WebhookProcessingResult
from db.unit_of_work import AsyncUnitOfWork

try:
    from fastapi import APIRouter, Header, HTTPException, Request, status

    HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    HAS_FASTAPI = False
    APIRouter = Any  # type: ignore[misc,assignment]

    class status:  # type: ignore[no-redef]
        HTTP_200_OK = 200
        HTTP_400_BAD_REQUEST = 400
        HTTP_401_UNAUTHORIZED = 401
        HTTP_422_UNPROCESSABLE_ENTITY = 422

    class HTTPException(Exception):  # type: ignore[no-redef]
        def __init__(self, status_code: int, detail: str) -> None:
            self.status_code = status_code
            self.detail = detail


logger = logging.getLogger("mandate_gateway.routers.webhooks")

if HAS_FASTAPI:
    webhooks_router: Any = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])
else:

    class DummyRouter:
        def post(self, *args: Any, **kwargs: Any) -> Callable:
            def decorator(func: Callable) -> Callable:
                return func

            return decorator

    webhooks_router: Any = DummyRouter()  # type: ignore[no-redef]


@webhooks_router.post("/razorpay", status_code=200)
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(None, alias="X-Razorpay-Signature"),
    x_razorpay_event_id: str | None = Header(None, alias="X-Razorpay-Event-Id"),
) -> dict[str, Any]:
    """
    Ingest and process Razorpay webhook notifications.

    Requires:
      - Raw request body (bytes) for HMAC-SHA256 signature verification.
      - Header 'X-Razorpay-Signature' containing HMAC digest.
      - Optional Header 'X-Razorpay-Event-Id'.
    """
    raw_body = await request.body()
    engine = WebhookEngine()

    async with AsyncUnitOfWork() as uow:
        result: WebhookProcessingResult = await engine.async_process_webhook(
            uow=uow,
            raw_payload=raw_body,
            signature=x_razorpay_signature,
            event_id=x_razorpay_event_id,
        )
        if result.success:
            await uow.commit()
            return {
                "status": "ok",
                "event_id": result.event_id,
                "transaction_id": result.transaction_id,
                "state": result.state.value if result.state else None,
                "is_duplicate": result.is_duplicate,
                "detail": result.rejection_detail,
            }
        else:
            # Determine appropriate HTTP status code based on rejection reason
            status_code = 400
            if result.rejection_reason is RejectionReason.METHOD_NOT_AUTHORIZED:
                status_code = 401
            elif result.rejection_reason is RejectionReason.AUTHORIZATION_EXPIRED:
                status_code = 400

            raise HTTPException(
                status_code=status_code,
                detail=result.rejection_detail or "Webhook processing failed.",
            )

    raise HTTPException(
        status_code=400,
        detail="Webhook execution failed.",
    )
