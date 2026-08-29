# Runbook I — Provider Elevated Failure Rate & Webhook Attack

## Detection
- **Alert**: `provider_failure_rate_high`, `provider_latency_critical`, OR `webhook_signature_attack_rate`.
- **Condition**: Provider failure rate > 10%, latency > 2000ms, or invalid webhook signature count > 20/min.

## Impact
- High payment decline rate or webhook endpoint abuse.

## Immediate Safety Rule
> [!IMPORTANT]
> Verify Razorpay API status page and webhook HMAC signatures. Reject invalid webhook signatures fail-closed.

## Diagnosis Steps
1. Inspect provider response error codes (`payment_execution_failure_total`).
2. Verify webhook signature verification failure count (`webhook_signature_failures_total`).
3. Check status of Razorpay payment gateway API.

## Verification Steps
1. Execute test health ping to Razorpay API gateway endpoint.

## Recovery Steps
1. For webhook signature attack: Enable WAF rate-limiting on `/webhooks/razorpay` endpoint and rotate webhook secret.
2. For provider degradation: Enable circuit breaker / queue reconciliation mode for non-realtime payments.

## Escalation Criteria
- Escalates to Merchant Operations and Account Manager if provider outage exceeds 30 minutes.

## Forbidden Actions
- Do NOT bypass HMAC signature validation for webhooks.
