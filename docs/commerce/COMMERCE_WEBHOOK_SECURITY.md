# RAZERPAY — Commerce Webhook Security (M25)

## Overview
`CommerceWebhookHandler` ([`apps/api/commerce/webhooks.py`](file:///home/santhakumar/Desktop/Razorpay/apps/api/commerce/webhooks.py)) verifies incoming merchant webhook events (`order.created`, `order.confirmed`, `order.cancelled`, `payment.accepted`, `payment.failed`).

## Security Controls
1. **HMAC-SHA256 Signature Verification (`x-merchant-signature`)**: Verifies signature against merchant webhook secret. Unsigned or mismatched webhooks return HTTP 401.
2. **Timestamp Freshness (`x-timestamp`)**: Rejects webhook events older than 300 seconds to prevent replay attacks.
3. **Event Idempotency (`x-event-id`)**: Tracks processed `event_id` tokens to ensure duplicate webhooks are processed idempotently without re-triggering side effects.
