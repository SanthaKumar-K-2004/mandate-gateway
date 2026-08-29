# Runbook E — Transactional Outbox Event Backlog Growing

## Detection
- **Alert**: `outbox_backlog_critical`
- **Condition**: `outbox_events_pending > 100` OR `outbox_oldest_pending_age > 60s`.

## Impact
- Eventual consistency delay for downstream subscribers and event listeners. (Payments remain fully consistent and committed).

## Immediate Safety Rule
> [!NOTE]
> Pending outbox events are safely stored in database `outbox_events` table. Payments are safe.

## Diagnosis Steps
1. Query outbox status counts: `SELECT status, count(*) FROM outbox_events GROUP BY status;`
2. Check outbox worker container process status: `docker logs mandate-outbox-worker`.
3. Inspect outbox dispatch latency metric: `outbox_processing_latency`.

## Verification Steps
1. Determine if outbox worker process is running and actively claiming batches.

## Recovery Steps
1. Restart outbox worker process.
2. Scale outbox worker instances if backlog processing throughput is insufficient.

## Escalation Criteria
- Escalates to Platform Engineering if outbox table backlog exceeds 10,000 events.

## Forbidden Actions
- Do NOT truncate `outbox_events` table.
