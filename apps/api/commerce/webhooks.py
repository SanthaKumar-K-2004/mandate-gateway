"""
Mandate Gateway — Commerce Webhook Handler (M25)
Workstream 3 — Processes and verifies incoming merchant webhooks.
Enforces HMAC-SHA256 signature verification, timestamp freshness (max 300s),
and event idempotency.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from apps.api.commerce.order_verification import OrderVerificationEngine


class WebhookValidationError(RuntimeError):
    """Raised when incoming merchant webhook validation fails."""

    pass


class CommerceWebhookHandler:
    """Production-grade Signed Merchant Webhook Processor."""

    def __init__(
        self,
        order_verifier: Optional[OrderVerificationEngine] = None,
        webhook_secret: str = "whsec_cafe_acme_live_m25",
    ) -> None:
        self.order_verifier = order_verifier or OrderVerificationEngine()
        self.webhook_secret = webhook_secret
        self._processed_events: Set[str] = set()

    def verify_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """Verify HMAC-SHA256 signature header."""
        if not raw_body or not signature_header:
            return False

        clean_sig = signature_header.replace("sha256=", "").strip()
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(clean_sig, expected)

    def process_webhook(
        self,
        raw_body: bytes,
        signature: str,
        event_id: str,
        timestamp_header: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate and process incoming merchant webhook event.
        1. Verify HMAC-SHA256 signature
        2. Timestamp freshness validation (<= 300 seconds)
        3. Event idempotency check (reject duplicate event_id)
        """
        # 1. Signature Verification
        if not self.verify_signature(raw_body, signature):
            raise WebhookValidationError(
                "Security Rejection: Invalid HMAC-SHA256 merchant webhook signature."
            )

        # 2. Timestamp Freshness Check
        try:
            event_ts = int(timestamp_header)
            now_ts = int(time.time())
            if abs(now_ts - event_ts) > 300:
                raise WebhookValidationError(
                    f"Security Rejection: Webhook timestamp expired ({abs(now_ts - event_ts)}s old > 300s limit)."
                )
        except ValueError:
            raise WebhookValidationError("Security Rejection: Invalid webhook timestamp header.")

        # 3. Event Idempotency Check
        if event_id in self._processed_events:
            return {
                "status": "DUPLICATE",
                "message": f"Webhook event '{event_id}' already processed.",
                "event_id": event_id,
            }

        self._processed_events.add(event_id)

        # 4. Dispatch Event
        event_type = payload.get("event") or payload.get("event_type") or "order.updated"
        event_data = payload.get("data") or payload

        merchant_order_id = event_data.get("merchant_order_id") or event_data.get("order_id") or ""
        payment_transaction_id = (
            event_data.get("payment_transaction_id") or event_data.get("transaction_id") or ""
        )
        outcome_id = event_data.get("outcome_id") or f"outcome_{merchant_order_id}"

        if event_type in ("order.confirmed", "order.created", "payment.accepted"):
            authoritative_ev = {
                "amount_paise": str(event_data.get("amount_paise", 0)),
                "currency": str(event_data.get("currency", "INR")),
                "source": "merchant_signed_webhook",
                "event_id": event_id,
                "event_type": event_type,
            }
            outcome = self.order_verifier.verify_order_outcome(
                outcome_id=outcome_id,
                payment_transaction_id=payment_transaction_id,
                merchant_order_id=merchant_order_id,
                authoritative_evidence=authoritative_ev,
            )
            return {
                "status": "SUCCESS",
                "event_id": event_id,
                "event_type": event_type,
                "order_status": outcome.order_status.value,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "status": "PROCESSED",
            "event_id": event_id,
            "event_type": event_type,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
