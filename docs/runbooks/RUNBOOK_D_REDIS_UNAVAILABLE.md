# Runbook D — Redis Cache / Lock Service Unavailable

## Detection
- **Alert**: `/ready` endpoint returns HTTP 503 (in production mode).
- **Log Event**: `dependency.failed` for Redis.

## Impact
- Concurrent distributed lock operations fail closed for safety. Non-critical caching degrades to primary database.

## Immediate Safety Rule
> [!IMPORTANT]
> Distributed locks for concurrent execution MUST fail closed when Redis is unavailable.

## Diagnosis Steps
1. Test Redis connectivity: `redis-cli ping`.
2. Check Redis container status: `docker logs mandate-redis`.
3. Inspect memory usage: `info memory`.

## Verification Steps
1. Verify Redis is accepting TCP connections on port 6379.

## Recovery Steps
1. Restart Redis container or failover to Redis replica.
2. Confirm Redis reconnection in application logs.
3. Verify `/ready` endpoint returns HTTP 200 OK.

## Escalation Criteria
- Escalates to Site Reliability Team if Redis cluster fails to elect a primary node.

## Forbidden Actions
- Do NOT disable lock checks under concurrent execution.
