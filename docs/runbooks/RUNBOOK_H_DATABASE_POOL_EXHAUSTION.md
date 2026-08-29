# Runbook H — PostgreSQL Connection Pool Exhaustion

## Detection
- **Alert**: `database_connection_exhaustion`
- **Condition**: `active_db_connections >= pool_max_size`.

## Impact
- High database connection queue wait time, request timeouts, and 503 readiness degradation.

## Immediate Safety Rule
> [!CAUTION]
> Do NOT blindly increase pool size beyond PostgreSQL `max_connections` limit.

## Diagnosis Steps
1. Query active PostgreSQL connections: `SELECT count(*), state FROM pg_stat_activity GROUP BY state;`
2. Identify long-running transactions: `SELECT pid, now() - query_start AS duration, query FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC;`
3. Inspect application logs for unclosed SQLAlchemy sessions.

## Verification Steps
1. Confirm if active connections are holding locks or stuck waiting on external responses.

## Recovery Steps
1. Terminate idle/stuck connections: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE duration > INTERVAL '5 minutes';`
2. Restart worker instances to flush connections.
3. Scale PostgreSQL connection pooler (e.g. PgBouncer).

## Escalation Criteria
- Escalates to Site Reliability Team if connection leak persists across deployments.

## Forbidden Actions
- Do NOT disable connection pool timeout limits.
