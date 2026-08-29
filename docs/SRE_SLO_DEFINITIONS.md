# Mandate Gateway — Production SRE SLIs, SLOs & Alerting Specifications

This document specifies the authoritative Service Level Indicators (SLIs), Service Level Objectives (SLOs), Error Budget calculations, Alerting Rules, and Dependency Degradation behaviors for the **Mandate Gateway** production platform.

---

## 1. Service Level Objectives (SLOs)

| Metric Name | Target SLO | Window | SLI Measurement | Warning Threshold | Critical Threshold |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **API Availability** | `99.9%` | `30d` | `(Non-5xx Requests / Total Requests) * 100` | `99.95%` | `99.90%` |
| **Payment Correctness** | `100.0%` | `30d` | `(Zero Double-Spend Executions / Total Executions) * 100` | `100.0%` | `100.0%` |
| **Execution Latency** | `99.0%` | `30d` | `(Executions Completed < 500ms / Total Executions) * 100` | `99.5%` | `99.0%` |
| **Recovery Time** | `99.9%` | `30d` | `(Stuck Executions Reconciled < 60s / Total Stuck) * 100` | `99.95%` | `99.90%` |
| **Outbox Delivery Delay**| `99.9%` | `30d` | `(Outbox Events Dispatched < 5s / Total Events) * 100` | `99.95%` | `99.90%` |

---

## 2. Error Budget Calculation Formula

$$\text{Error Budget Consumed (\%)} = \min\left(100.0, \frac{\text{Failed Events}}{\text{Total Events} \times (1.0 - \text{SLO Target})}\right) \times 100$$

$$\text{Error Budget Remaining (\%)} = 100.0 - \text{Error Budget Consumed (\%)}`$$

---

## 3. Production Alert Specifications

1. **`audit_chain_verification_failure`** (Severity: `CRITICAL`)
   - **Trigger**: `audit_chain_verification_failures_total > 0`
   - **Window**: `1m`
   - **Runbook**: `RUNBOOK_F_AUDIT_VERIFICATION_FAILURE.md`

2. **`receipt_signature_verification_failure`** (Severity: `CRITICAL`)
   - **Trigger**: `receipt_verification_failures_total > 0`
   - **Window**: `1m`
   - **Runbook**: `RUNBOOK_G_RECEIPT_VERIFICATION_FAILURE.md`

3. **`execution_unknown_backlog`** (Severity: `HIGH`)
   - **Trigger**: `payment_execution_unknown_total > 5`
   - **Window**: `5m`
   - **Runbook**: `RUNBOOK_B_PROVIDER_TIMEOUT.md`

4. **`stuck_executing_transaction_age`** (Severity: `HIGH`)
   - **Trigger**: Transactions in `EXECUTING` state for `> 300s`
   - **Window**: `5m`
   - **Runbook**: `RUNBOOK_A_STUCK_EXECUTING.md`

5. **`outbox_backlog_critical`** (Severity: `HIGH`)
   - **Trigger**: `outbox_events_pending > 100` OR `outbox_oldest_pending_age > 60s`
   - **Window**: `2m`
   - **Runbook**: `RUNBOOK_E_OUTBOX_BACKLOG.md`

6. **`database_connection_exhaustion`** (Severity: `CRITICAL`)
   - **Trigger**: `active_db_connections >= pool_max_size`
   - **Window**: `1m`
   - **Runbook**: `RUNBOOK_H_DATABASE_POOL_EXHAUSTION.md`

7. **`provider_failure_rate_high`** (Severity: `HIGH`)
   - **Trigger**: `provider_failure_rate > 10%`
   - **Window**: `5m`
   - **Runbook**: `RUNBOOK_I_PROVIDER_ELEVATED_FAILURE_RATE.md`

8. **`provider_latency_critical`** (Severity: `HIGH`)
   - **Trigger**: `provider_latency p99 > 2000ms`
   - **Window**: `5m`
   - **Runbook**: `RUNBOOK_I_PROVIDER_ELEVATED_FAILURE_RATE.md`

9. **`webhook_signature_attack_rate`** (Severity: `HIGH`)
   - **Trigger**: `webhook_signature_failures_total > 20`
   - **Window**: `1m`
   - **Runbook**: `RUNBOOK_I_PROVIDER_ELEVATED_FAILURE_RATE.md`

10. **`recovery_failure_rate`** (Severity: `HIGH`)
    - **Trigger**: `recovery_failures > 3`
    - **Window**: `5m`
    - **Runbook**: `RUNBOOK_A_STUCK_EXECUTING.md`

---

## 4. Dependency Degradation Matrix

| Subsystem | State | Behavior Mode | Readiness HTTP Status | System Action |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** | Unavailable | `FAIL_CLOSED` | `503 Service Unavailable` | Reject new payment operations fail-closed. |
| **Redis (Lock)** | Unavailable | `FAIL_CLOSED` | `503 Service Unavailable` | Reject concurrent payment proposals. |
| **Redis (Cache)** | Unavailable | `SAFE_DEGRADATION` | `200 OK` | Bypass cache; read directly from database. |
| **Provider** | Unavailable | `RECONCILIATION` | `200 OK` | Hold in `EXECUTING`/`UNKNOWN` state for recovery scan. |
| **Telemetry Exporter**| Unavailable | `FAIL_OPEN` | `200 OK` | Log telemetry locally. Payments proceed safely. |
| **Outbox Worker** | Unavailable | `DURABLE_PENDING` | `200 OK` | Commit payment safely; leave outbox event `PENDING`. |
