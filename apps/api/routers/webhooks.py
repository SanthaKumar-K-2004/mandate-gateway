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


# --- Public Developer Webhook Management Endpoints (Workstream 4 & 5) ---

_in_memory_subscriptions: dict[str, dict[str, Any]] = {}
_in_memory_deliveries: list[dict[str, Any]] = []


@webhooks_router.post("/subscriptions", status_code=201, summary="Register Webhook Subscription")
async def create_webhook_subscription(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Registers an external webhook endpoint subscription for a merchant."""
    import uuid
    from datetime import datetime, timezone

    url = payload.get("url")
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(
            status_code=400, detail="Invalid webhook URL. Must begin with http:// or https://"
        )

    sub_id = f"sub_{uuid.uuid4().hex[:12]}"
    secret = payload.get("secret") or f"whsec_{uuid.uuid4().hex[:16]}"
    events = payload.get("events") or ["payment.captured", "payment.failed", "mandate.created"]

    record = {
        "subscription_id": sub_id,
        "merchant_id": payload.get("merchant_id", "mer_default"),
        "url": url,
        "events": events,
        "secret": secret,
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _in_memory_subscriptions[sub_id] = record

    return {
        "subscription_id": sub_id,
        "merchant_id": record["merchant_id"],
        "url": url,
        "events": events,
        "secret": secret,
        "status": "ACTIVE",
        "created_at": record["created_at"],
    }


@webhooks_router.get("/subscriptions", status_code=200, summary="List Webhook Subscriptions")
async def list_webhook_subscriptions(
    merchant_id: str | None = None,
) -> dict[str, Any]:
    """Lists registered webhook subscriptions."""
    subs = list(_in_memory_subscriptions.values())
    if merchant_id:
        subs = [s for s in subs if s.get("merchant_id") == merchant_id]
    return {
        "count": len(subs),
        "subscriptions": [
            {
                "subscription_id": s["subscription_id"],
                "merchant_id": s["merchant_id"],
                "url": s["url"],
                "events": s["events"],
                "status": s["status"],
                "created_at": s["created_at"],
            }
            for s in subs
        ],
    }


@webhooks_router.patch(
    "/subscriptions/{subscription_id}", status_code=200, summary="Update Subscription Status"
)
async def update_webhook_subscription(
    subscription_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Updates webhook subscription status (ACTIVE / DISABLED)."""
    sub = _in_memory_subscriptions.get(subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Subscription '{subscription_id}' not found.")

    new_status = payload.get("status", "ACTIVE").upper()
    if new_status not in ("ACTIVE", "DISABLED"):
        raise HTTPException(status_code=400, detail="Status must be 'ACTIVE' or 'DISABLED'.")

    sub["status"] = new_status
    return {
        "subscription_id": subscription_id,
        "status": sub["status"],
        "updated_at": sub["created_at"],
    }


@webhooks_router.get("/deliveries", status_code=200, summary="List Webhook Delivery Records")
async def list_webhook_deliveries() -> dict[str, Any]:
    """Lists webhook delivery logs and retry statuses."""
    return {
        "count": len(_in_memory_deliveries),
        "deliveries": _in_memory_deliveries,
    }
