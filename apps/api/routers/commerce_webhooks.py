"""
Mandate Gateway — Commerce Webhooks Router (M25)
Workstream 3 — REST API endpoint for receiving signed merchant webhooks.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Request, status

from apps.api.commerce.webhooks import CommerceWebhookHandler, WebhookValidationError

router = APIRouter(prefix="/api/v1/commerce/webhooks", tags=["Commerce Webhooks"])

_webhook_handler = CommerceWebhookHandler()


@router.post("/merchant", summary="Receive Signed Merchant Webhook", status_code=status.HTTP_200_OK)
async def receive_merchant_webhook(
    request: Request,
    x_merchant_signature: str = Header(..., alias="x-merchant-signature"),
    x_event_id: str = Header(..., alias="x-event-id"),
    x_timestamp: str = Header(..., alias="x-timestamp"),
) -> Dict[str, Any]:
    """Receive and verify incoming HMAC-SHA256 signed merchant webhook."""
    raw_body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    try:
        result = _webhook_handler.process_webhook(
            raw_body=raw_body,
            signature=x_merchant_signature,
            event_id=x_event_id,
            timestamp_header=x_timestamp,
            payload=payload,
        )
        return result
    except WebhookValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err),
        )
