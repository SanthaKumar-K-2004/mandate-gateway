# Mandate Gateway — M19 Production Deployment Guide

## Section 1 — Environment Variable Template (`.env.production.template`)

```ini
# Application Core Context
APP_ENV=production
APP_NAME=mandate-gateway
LOG_LEVEL=INFO
PORT=8000

# PostgreSQL Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=mandate_gateway
POSTGRES_USER=postgres_prod_user
POSTGRES_PASSWORD=CHANGE_ME_PRODUCTION_DB_PASSWORD

# Redis Cache / Distributed Locking
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Security & Authorization
OPERATOR_SECRET_TOKEN=CHANGE_ME_PRODUCTION_OPERATOR_TOKEN
RAZORPAY_API_KEY_SECRET=CHANGE_ME_PRODUCTION_API_KEY_SECRET
```

---

## Section 2 — Production Configuration Validation

Before starting services, run the configuration validation check:

```bash
python3 -c "from apps.api.config.settings import Settings; Settings.from_env()"
```

If any mandatory production secrets use default or insecure values (e.g. `postgres`, `password`, `123456`), the validation engine will fail-fast and reject process startup.

---

## Section 3 — Database Migration Strategy

Run database schema migrations before deploying new container revisions:

```bash
# Execute Alembic database migrations to head
alembic upgrade head
```

---

## Section 4 — Container & Process Topology Startup Commands

### 1. Docker Compose Production Stack Startup
```bash
docker compose -f docker-compose.yml up -d
```

### 2. Standalone Container / Worker Process Commands
- **API Instance**:
  ```bash
  python3 -m apps.api.main
  ```
- **Outbox Worker**:
  ```bash
  python3 -m apps.workers.outbox_worker
  ```
- **Recovery Worker**:
  ```bash
  python3 -m apps.workers.recovery_worker
  ```

---

## Section 5 — Production Health Check Probes

- **Liveness Probe**: `GET http://localhost:8000/health/live` (HTTP 200 OK if process alive)
- **Readiness Probe**: `GET http://localhost:8000/health/ready` (HTTP 200 OK if DB & Redis connected)
- **Dependencies Probe**: `GET http://localhost:8000/health/dependencies` (HTTP 200 OK)
- **Prometheus Metrics**: `GET http://localhost:8000/metrics`
- **Product Dashboard**: `GET http://localhost:8000/dashboard`

---

## Section 6 — Rollback Procedure

In case of deployment failure or critical infrastructure degradation:

1. Stop application containers:
   ```bash
   docker compose down
   ```
2. Revert image tags to previous certified release tag (e.g. `v0.18.0`).
3. Re-run migration rollback if applicable:
   ```bash
   alembic downgrade -1
   ```
4. Restart application containers with previous tag:
   ```bash
   docker compose up -d
   ```

---

## Section 7 — Production Release Verification Checklist

- [ ] `PROJECT_CONTEXT.md` SHA-256 checksum verified (`2b62d52aa707bc9bb5df60d93b04f60933562e69af8068c46cc3b6cdc2eb670a`).
- [ ] Automated quality gates passed cleanly (`make check`).
- [ ] No hardcoded passwords or plain text credentials committed.
- [ ] Containers run as non-root user (`appuser:appgroup`).
- [ ] Database volume persistence configured (`postgres_data`).
- [ ] Single-use nonces and atomic budget locks active.
- [ ] Multi-instance duplicate payment dispatches verified = **0**.
