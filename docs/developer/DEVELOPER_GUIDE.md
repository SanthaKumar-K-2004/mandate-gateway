# Razerpay Mandate Gateway — Developer Integration & Quickstart Guide

Welcome to the **Razerpay Mandate Gateway Developer Platform**. This guide covers full integration patterns for integrating autonomous payment mandates, API authentication, idempotency controls, action receipt verification, and webhook delivery.

---

## 1. Quickstart & Server Startup

### Installation & Environment Setup
Clone the repository and install runtime dependencies:

```bash
pip install -e .
```

Start the API service in development or production mode:

```bash
python3 -m apps.api.main
```

The gateway listens at `http://localhost:8000`.

---

## 2. Authentication Model

All REST API requests require standard HTTP Bearer token authentication and merchant tenant isolation headers:

```http
Authorization: Bearer rzp_live_demo_token_123
X-Merchant-ID: mer_acme_corp
```

If authorization fails or headers are omitted, the API responds with HTTP 401:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Operator authorization credentials required.",
    "request_id": "req_12345678"
  }
}
```

---

## 3. API Versioning

All public API endpoints are versioned under `/api/v1/`:
- `GET /api/v1/merchants`
- `POST /api/v1/mandates`
- `POST /api/v1/payments`
- `POST /api/v1/webhooks/subscriptions`

Backward-incompatible changes will be introduced under new version prefixes (`/api/v2/`).

---

## 4. Request ID & Correlation Tracking

Every API request accepts an optional `X-Request-ID` header. If absent, the gateway generates a UUID string (`req_<uuid>`):

```http
X-Request-ID: req_client_98127391
```

The `X-Request-ID` is returned in all HTTP response headers, error response payloads, and audit ledger logs for microsecond request correlation.

---

## 5. Idempotency API Contract

To guarantee that **NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE**, all mutating payment operations require an idempotency key:

```http
X-Idempotency-Key: idemp_order_98123
```

### Idempotency Behavior
1. **First Request**: Payment executes, state committed, response cached.
2. **Identical Replay**: Returns cached response with header `X-Cache-Replay: true`.
3. **Payload Mutation Conflict**: If a client re-uses an idempotency key with a modified payload or different merchant ID, the engine fails closed with HTTP 409:

```json
{
  "error": {
    "code": "IDEMPOTENCY_CONFLICT",
    "message": "Idempotency key payload mismatch.",
    "request_id": "req_98123"
  }
}
```

---

## 6. Mandate Lifecycle & Payment Execution

1. **Merchant Policy Registration**: Define autonomous spending limits and step-up thresholds.
2. **Mandate Creation**: Issue daily budget cap for a buyer (`daily_budget_paise: 100000`).
3. **Payment Proposal**: Propose cart item list.
4. **Policy & Budget Evaluation**: System checks daily budget availability.
5. **Execution**: If authorized, atomic budget reservation lock is acquired and payment dispatched to provider.

---

## 7. Action Receipts & Cryptographic Verification

Every successful payment execution generates an immutable, Ed25519/SHA-256 signed Action Receipt (`rcpt_<id>`).

Verify receipt authenticity via API:

```http
POST /internal/operations/receipts/verify?payload_hash=...&signature_hex=...
```

---

## 8. Webhooks & Delivery Reliability

### Webhook Subscription Registration
```http
POST /api/v1/webhooks/subscriptions
Content-Type: application/json

{
  "url": "https://merchant.example.com/webhooks/razerpay",
  "events": ["payment.captured", "payment.failed"],
  "secret": "whsec_super_secret_key"
}
```

### Signature Verification
Webhooks include an `X-Razorpay-Signature` header computed as:

```text
HMAC-SHA256(raw_request_body, secret)
```

Verify signature in Python using the official SDK:

```python
from razerpay import RazerpayWebhookVerifier

is_valid = RazerpayWebhookVerifier.verify_signature(
    raw_payload=request_body_bytes,
    signature=headers["X-Razorpay-Signature"],
    secret="whsec_super_secret_key"
)
```

---

## 9. Python SDK Usage Example

```python
from razerpay import RazerpayClient, RazerpayConfig

client = RazerpayClient(RazerpayConfig(
    base_url="http://localhost:8000",
    api_key="rzp_live_demo_token_123",
    merchant_id="mer_acme_corp"
))

# 1. Create Mandate
mandate = client.create_mandate(buyer_id="buy_user_101", daily_budget_paise=50000)

# 2. Submit Payment
payment = client.submit_payment(
    mandate_id=mandate.mandate_id,
    amount_paise=25000,
    idempotency_key="idemp_order_550"
)

print(f"Payment State: {payment.state}, Receipt: {payment.action_receipt_signature}")
```

---

## 10. Sandbox Guidance

For testing in local sandbox environments, use `APP_ENV=development`. Sandbox payments execute against in-memory mock provider boundaries without real monetary movement.
