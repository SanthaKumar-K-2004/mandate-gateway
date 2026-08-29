# Runbook C — PostgreSQL Database Unavailable

## Detection
- **Alert**: `/ready` endpoint returns HTTP 503.
- **Log Event**: `dependency.failed` for PostgreSQL.

## Impact
- All new payment operations fail closed safely.

## Immediate Safety Rule
> [!CAUTION]
> Do NOT introduce in-memory fallbacks for database mutations.

## Diagnosis Steps
1. Test database connectivity: `pg_isready -h localhost -p 5432`.
2. Inspect PostgreSQL container logs: `docker logs mandate-postgres`.
3. Check disk space and memory utilization on database host.

## Verification Steps
1. Verify database process status and primary connection listener.

## Recovery Steps
1. Restart PostgreSQL container or failover to standby replica.
2. Verify connection pool reconnects automatically.
3. Confirm `/ready` endpoint returns HTTP 200 OK.

## Escalation Criteria
- Escalates to Database Administrator immediately if data disk corruption or unrecoverable WAL failure occurs.

## Forbidden Actions
- Do NOT bypass database checks or force `/ready` to return 200 OK.
