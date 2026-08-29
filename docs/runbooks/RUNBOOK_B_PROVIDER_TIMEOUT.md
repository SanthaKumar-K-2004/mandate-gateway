# Runbook B — Provider Timeout & Ambiguous Result Handling

## Detection
- **Alert**: `execution_unknown_backlog`
- **Condition**: `payment_execution_unknown_total > 5` within 5 minutes.

## Impact
- Ambiguous payment outcomes requiring status reconciliation.

## Immediate Safety Rule
> [!IMPORTANT]
> Provider timeouts must preserve `UNKNOWN` provider status until status query succeeds. Do NOT guess the outcome.

## Diagnosis Steps
1. Inspect provider gateway network connectivity and DNS resolution.
2. Check provider status API latency metrics (`provider_latency`).
3. Check provider status endpoint response code (`504 Gateway Timeout` vs `502 Bad Gateway`).

## Verification Steps
1. Issue status query request to Razorpay status endpoint using transaction `idempotency_key`.

## Recovery Steps
1. Trigger automatic status reconciliation daemon.
2. If status query confirms success -> transition transaction to `SUCCESS` and generate Ed25519 receipt.
3. If status query confirms failure -> transition transaction to `FAILED`.

## Escalation Criteria
- Escalates to Infrastructure Team if provider gateway timeout persists > 15 minutes.

## Forbidden Actions
- Do NOT retry raw payment creation request with a new idempotency key.
