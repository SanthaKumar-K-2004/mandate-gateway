# OPERATIONAL RUNBOOKS — DISASTER RECOVERY & RELEASE CERTIFICATION (M17)

## Executive Summary
This document provides production operator instructions for diagnosing, recovering, and verifying Razorpay Mandate Gateway operations across 12 disaster recovery and operational failure scenarios.

All operational procedures must strictly preserve the primary invariant:
> **"NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE."**

---

## Runbook Index
* **RUNBOOK-01**: `EXECUTING` Transaction Stuck
* **RUNBOOK-02**: `UNKNOWN` Provider Outcome Resolution
* **RUNBOOK-03**: Database Infrastructure Outage & Recovery
* **RUNBOOK-04**: Redis Infrastructure Outage & Failover
* **RUNBOOK-05**: Outbox Backlog Backpressure Management
* **RUNBOOK-06**: Recovery Worker Process Failure & Restart
* **RUNBOOK-07**: Audit Ledger Hash Chain Corruption Investigation
* **RUNBOOK-08**: Database Schema Migration Mismatch
* **RUNBOOK-09**: Failed Release Deployment Promotion Abort
* **RUNBOOK-10**: Safe Application Rollback Procedure
* **RUNBOOK-11**: Database Snapshot Backup & Restoration
* **RUNBOOK-12**: Full Site Disaster Recovery & Multi-Service Restoration

---

### RUNBOOK-01: `EXECUTING` Transaction Stuck
**Trigger**: Alert `TRANSACTION_STUCK_EXECUTING` or recovery scan detecting transactions in `EXECUTING` state past 30 seconds.
**Procedure**:
1. Check recovery worker process status (`make status` or `ProcessTopologyManager`).
2. Query provider API using provider payment reference (`provider_payment_id`).
3. If provider confirms SUCCESS/PAID -> execute reconciliation to transition transaction to `SUCCESS`.
4. If provider confirms FAILED/DECLINED -> transition transaction to `FAILURE`.
5. If provider response is ambiguous or unavailable -> retain status as `UNKNOWN` and state as `EXECUTING`. NEVER force state to `COMMITTED` without proof.

### RUNBOOK-02: `UNKNOWN` Provider Outcome Resolution
**Trigger**: Alert `PROVIDER_UNKNOWN_OUTCOME`.
**Procedure**:
1. Inspect forensic event stream for the correlation ID (`GET /internal/operations/transactions/{id}/timeline`).
2. Verify outbox event backlog and execution attempt ownership record.
3. Perform provider polling. If provider returns verified status, update via reconciliation worker.
4. Maintain `EXECUTING` state while outcome is unconfirmed.

### RUNBOOK-03: Database Infrastructure Outage & Recovery
**Trigger**: Liveness/Readiness probe failure with `PostgreSQL database unavailable`.
**Procedure**:
1. API service automatically returns HTTP 503 Readiness Unavailable.
2. In-flight requests roll back fail-closed; no uncommitted data is saved.
3. Restore database cluster or switch connection string to failover standby.
4. Run `MigrationGuard` validation (`python -m apps.api.deployment.migration_guard`).
5. Verify `/ready` endpoint returns HTTP 200 OK before routing payment traffic.

### RUNBOOK-04: Redis Infrastructure Outage & Failover
**Trigger**: Redis health check failing on `/ready` endpoint.
**Procedure**:
1. API gracefully degrades or returns 503 depending on strictness policy (`APP_ENV=production`).
2. Restore Redis container or cluster node.
3. Upon reconnect, verify atomic lock acquisition and rate limiter counter reset.

### RUNBOOK-05: Outbox Backlog Backpressure Management
**Trigger**: Alert `OUTBOX_BACKLOG_ELEVATED` (> 1000 pending outbox events).
**Procedure**:
1. Check outbox worker process logs for downstream transport errors.
2. Scale outbox worker process instances (`ProcessRole.OUTBOX_WORKER`).
3. Outbox workers process events idempotently using row locking (`FOR UPDATE`).

### RUNBOOK-06: Recovery Worker Process Failure & Restart
**Trigger**: Recovery worker process crash signal or health check timeout.
**Procedure**:
1. Process supervisor restarts worker automatically.
2. Worker acquires locks and resumes scanning stuck transactions without duplicate dispatches.

### RUNBOOK-07: Audit Ledger Hash Chain Corruption Investigation
**Trigger**: Alert `AUDIT_CHAIN_CORRUPTED`.
**Procedure**:
1. Execute `uow.audit.verify_chain()`.
2. Locate breaking sequence number `N` where `previous_hash != event_{N-1}.event_hash`.
3. Quarantine compromised node; preserve forensic log data for security review.
4. Restore from latest verified `BackupSnapshot`.

### RUNBOOK-08: Database Schema Migration Mismatch
**Trigger**: `MigrationGuard` flagging revision mismatch during deployment startup.
**Procedure**:
1. Halt deployment pipeline (`ReleaseOrchestrator` Stage 3 fails).
2. Execute `alembic upgrade head`.
3. Re-run `MigrationGuard` check until status returns `UP_TO_DATE`.

### RUNBOOK-09: Failed Release Deployment Promotion Abort
**Trigger**: Pre-promotion readiness check or smoke test failure.
**Procedure**:
1. `ReleaseOrchestrator` aborts candidate promotion.
2. Traffic routing remains pinned to previous stable deployment version.
3. Perform post-mortem analysis using build manifest metadata.

### RUNBOOK-10: Safe Application Rollback Procedure
**Trigger**: Post-deployment instability or elevated HTTP 5xx rate.
**Procedure**:
1. Run `RollbackManager.evaluate_rollback_safety(uow)`.
2. Verify pending outbox events and `EXECUTING` transactions are preserved.
3. Roll back application container image. DO NOT execute database `DOWN` migrations.

### RUNBOOK-11: Database Snapshot Backup & Restoration
**Trigger**: Disaster recovery event or staging environment refresh.
**Procedure**:
1. Export snapshot: `BackupRestoreManager.export_database_snapshot(uow)`.
2. Verify snapshot SHA-256 checksum.
3. Restore into clean environment: `BackupRestoreManager.restore_database_snapshot(uow, snapshot)`.
4. Validate 13 post-restore invariants via `verify_restore_integrity`.

### RUNBOOK-12: Full Site Disaster Recovery & Multi-Service Restoration
**Trigger**: Region outage or data center disaster.
**Procedure**:
1. Provision clean compute & database infrastructure.
2. Restore latest verified `BackupSnapshot`.
3. Verify `ReleaseManifest` checksums (`verify_release_manifest`).
4. Start API, Outbox Worker, and Recovery Worker topology.
5. Confirm liveness, readiness, audit chain validity, and receipt verification before opening ingress.
