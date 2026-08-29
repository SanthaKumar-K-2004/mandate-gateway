# Mandate Gateway — Database Backup, Restore & Operational Discipline Runbook

## Section M10 — Operational Discipline, Backup Procedures & Post-Restore Validation

---

### 1. Authoritative Data Inventory

The Mandate Gateway database (`mandate_gateway`) stores authoritative payment lifecycle state across 14 tables:

| Table Category | Tables Included | Backup Criticality |
| :--- | :--- | :---: |
| **Merchant & Policy** | `merchants`, `merchant_policies`, `products` | High |
| **Mandate & Budget** | `mandates`, `budgets` | Critical |
| **Transactions & Attempts** | `transactions`, `execution_attempts` | Critical |
| **Audit Ledger & Receipts** | `audit_events`, `action_receipts` | Immutable Critical |
| **Security Controls** | `nonces`, `replays`, `step_up_challenges` | Critical |
| **Infrastructure & Side Effects**| `outbox_events`, `webhook_deliveries` | High |

---

### 2. Backup Execution Procedure

Backups must be generated using `pg_dump` in PostgreSQL custom format (`-Fc`) using environment variables for credentials. Secrets must NEVER be written to shell scripts or command-line parameters.

```bash
# Set credentials safely in environment
export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_DB="${POSTGRES_DB:-mandate_gateway}"
export POSTGRES_USER="${POSTGRES_USER:-postgres}"
# PGPASSWORD supplied via secure secret manager or prompt

# Execute consistent database snapshot
pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "mandate_gateway_$(date +%Y%m%d_%H%M%S).dump"
```

---

### 3. Database Restoration Procedure

To restore a database snapshot into a clean or recovered environment:

```bash
# 1. Ensure mandate-gateway API and worker processes are STOPPED
# (Prevents partial concurrent writes during restore)

# 2. Restore PostgreSQL schema & records
pg_restore -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists "mandate_gateway_backup.dump"

# 3. Verify Alembic schema migration version
alembic current
alembic upgrade head
```

---

### 4. Post-Restore Integrity Validation

After database restoration, operators MUST execute the following 3-step validation pipeline before starting production API traffic:

1. **Schema Integrity Check**:
   ```bash
   python -m unittest tests/integration/test_m09_migration_discipline.py
   ```
2. **Audit Ledger & Receipt Cryptographic Verification**:
   ```bash
   python -m scripts.verify_receipt
   ```
3. **Application Readiness Probe**:
   ```bash
   curl -f http://localhost:8000/ready
   ```

---

### 5. Recovery & Worker Restart Operational Discipline

If API or worker processes were interrupted during restoration:
* `OutboxWorker` automatically resumes pending outbox events (`status = 'PENDING'`).
* `RecoveryWorker` automatically scans stuck transactions (`state = 'EXECUTING'`) and reconciles provider outcomes fail-closed.
