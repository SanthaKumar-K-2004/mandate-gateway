# RAZERPAY — Incident Response Playbook

## Emergency Scenarios & Remediation

### 1. High Idempotency Conflict Rate
- **Symptom**: Spikes in `payment_idempotency_conflicts_total`.
- **Cause**: Client retrying requests with duplicate idempotency keys.
- **Action**: Verify client SDK retry policy. Mandate Gateway will safely fail closed with HTTP 409 Conflict.

### 2. Connector Circuit Breaker OPEN
- **Symptom**: `commerce_circuit_breaker_state{connector="..."} == 1`.
- **Cause**: Upstream merchant endpoint timing out or returning 5xx.
- **Action**: Check upstream merchant API status. Once healthy, reset circuit breaker via `/api/v1/commerce/connectors/{id}/reset-circuit`.

### 3. Payment-Order Mismatch (Unresolved Transaction)
- **Symptom**: Spikes in `payment_order_mismatch_rejections_total`.
- **Cause**: Payment succeeded but merchant order creation failed or timed out.
- **Action**: Check `/api/v1/commerce/reconciliation/unresolved`. Trigger manual operations review.
