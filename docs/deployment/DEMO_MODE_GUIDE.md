# Safe Live Demo Mode Guide

## Overview

Mandate Gateway includes an isolated **Safe Live Demo Mode** (`DEMO_MODE=true`) that enables complete, interactive demonstration of end-to-end payment journeys without ever connecting to live production payment gateway endpoints or executing real financial debits.

---

## Key Guarantees

1. **Production Secret Isolation**: Demo mode uses a safe mock provider (`order_DemoSuccess`) and rejects real production provider credentials to prevent key mixing.
2. **Real Domain Flow Reuse**: Demo mode executes identical authorization engines, daily budget reservations, idempotency nonces, Ed25519 action receipt signatures, tamper-evident audit ledger hash chains, and transactional outbox events as production.
3. **Zero Financial Impact**: Demo mode dispatches zero live financial API calls.

---

## Triggering Demo Mode

### Via REST API Endpoint
```bash
POST /internal/operations/demo/journey
Headers:
  Authorization: Bearer rzp_live_operator_token_123
  X-Operator-Token: rzp_live_operator_token_123
```

### Response Example
```json
{
  "status": "SUCCESS",
  "transaction_id": "tx_demo_a1b2c3d4",
  "amount_paise": 25000,
  "state": "COMMITTED",
  "provider_reference": "order_DemoSuccess",
  "message": "Real end-to-end payment demo journey executed successfully through domain engine."
}
```
