# Runbook F — Audit Hash-Chain Verification Failure

## Detection
- **Alert**: `audit_chain_verification_failure`
- **Condition**: `audit_chain_verification_failures_total > 0`.

## Impact
- Potential audit ledger tampering or data corruption detected.

## Immediate Safety Rule
> [!CAUTION]
> Treat audit chain verification failure as a SECURITY INCIDENT. Halt non-essential write operations if unauthorized mutation is suspected.

## Diagnosis Steps
1. Execute audit chain verification tool: `python3 -m apps.api.security.verify_audit_chain`.
2. Identify break point in sequence numbers (`sequence_number`, `event_hash`, `previous_hash`).
3. Check database audit log access logs for direct manual `UPDATE` or `DELETE` statements.

## Verification Steps
1. Determine exact sequence number where `event_hash` calculation diverges from stored value.

## Recovery Steps
1. Isolate the affected database node.
2. Restore audit ledger records from cryptographic backup or immutable audit replica.

## Escalation Criteria
- Escalates immediately to Chief Information Security Officer (CISO) and Security Lead.

## Forbidden Actions
- Do NOT re-hash audit ledger with broken hashes without forensic data backup.
