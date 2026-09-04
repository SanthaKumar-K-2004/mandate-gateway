# RAZORPAY — Agentic Payment Infrastructure Specification

## Overview

The **Razorpay Agentic Payment Infrastructure** provides a unified payment execution and authorization abstraction supporting:
1. **Razorpay Test Mode Client (`RazorpayClient`)**: Production-grade connector to `https://api.razorpay.com/v1` supporting test order creation, payment fetching, capture, and HMAC-SHA256 signature verification.
2. **x402 HTTP Payment Protocol Compatibility (`X402PaymentProtocol`)**: Standardized HTTP 402 Payment Required headers and cryptographic proof generation for paid API microservices.
3. **UAP-Aligned Authorization Layer (`UAPAuthorizationLayer`)**: Bounded delegation tokens enabling user-defined spending caps and merchant category scoping.

---

## 1. Razorpay Test-Mode Connector Client

### Base Endpoint & Configuration
- Base URL: `https://api.razorpay.com/v1`
- Currency / Units: Minor units (`paise` integer, e.g. 29900 = ₹299.00)
- Execution Mode: `TEST` / Sandbox mode by default (`RAZORPAY_MODE=test`)

### Key Operations

```python
# Create Test Order
order = client.create_test_order(
    amount_paise=29900,
    currency="INR",
    receipt="rcpt_coffee_01",
    notes={"agent_id": "shopping_agent_01"}
)

# Signature Verification
is_valid_wh = client.verify_webhook_signature(webhook_body, signature_header, webhook_secret)
is_valid_checkout = client.verify_payment_signature(order_id, payment_id, checkout_signature)
```

---

## 2. Invariants & Financial Safety Rules

1. **NO DUAL EXECUTION**: No payment effect may execute twice. Replay attempts on single-use authorization tokens are rejected fail-closed.
2. **INTEGER PAISE ACCURACY**: All monetary amounts are handled strictly as 64-bit integers in paise units. Floating-point currency representation is forbidden in financial evaluation routines.
3. **INTELLIGENCE / EXECUTION SEPARATION**: LLM and ML outputs provide reasoning and risk scoring signals only. They have zero direct execution authority.
4. **CRYPTO AUDIT TRAIL**: Every payment lifecycle event is recorded in an immutable SHA-256 audit ledger.
