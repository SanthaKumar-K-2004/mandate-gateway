# Runbook A — Transaction Stuck in EXECUTING State

## Detection
- **Alert**: `stuck_executing_transaction_age`
- **Condition**: Transaction remains in `EXECUTING` state for `> 300` seconds.

## Impact
- Buyer experience delay.
- Incomplete financial state reconciliation.

## Immediate Safety Rule
> [!CAUTION]
> NEVER manually mark an `UNKNOWN` or `EXECUTING` provider transaction as `COMMITTED` or `SUCCESS` without explicit Razorpay provider API status reconciliation evidence.

## Diagnosis Steps
1. Retrieve transaction record: `SELECT * FROM transactions WHERE state = 'EXECUTING' AND updated_at < NOW() - INTERVAL '5 minutes';`
2. Check execution attempts log: `SELECT * FROM execution_attempts WHERE transaction_id = '<tx_id>';`
3. Inspect provider HTTP logs for timeouts or socket resets.

## Verification Steps
1. Query provider API for status of `idempotency_key` or `provider_reference`.
2. Determine if payment was authorized/captured at provider or never received.

## Recovery Steps
1. Execute status reconciliation via PaymentExecutionService `reconcile_payment_status(tx_id)`.
2. If provider confirmed payment -> transition transaction to `SUCCESS` / `COMMITTED`.
3. If provider confirms no payment -> transition transaction to `FAILED`.

## Escalation Criteria
- Escalates to L2 On-Call Engineer if > 10 transactions stuck concurrently.

## Forbidden Actions
- Do NOT delete transaction records from database.
- Do NOT re-dispatch payment without idempotency check.
