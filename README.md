# Mandate Gateway

> A deterministic trust layer between an untrusted AI shopping agent and the official Razorpay MCP execution boundary.

---

## Core Principle

```text
AI decides.
Policy authorizes.
Razorpay executes.
Cryptography proves.
```

### Critical Security Invariant

> **The LLM is never the financial authorization authority.**

Mandate Gateway treats the AI agent and external product catalog data as untrusted inputs. Financial authorization decisions are computed deterministically by the Gateway policy engine using explicit buyer mandates and merchant AI commerce policies. No money movement action reaches the Razorpay execution boundary without signed, bounded, and audited Gateway authorization.

---

## Architecture Summary

Mandate Gateway enforces two-sided trust and deterministic financial execution across distinct architectural zones:

1. **Application Layer (`apps/`)**:
   - `apps/web`: Next.js control center UI for buyers, merchants, transactions, audit trails, and red-team chaos labs.
   - `apps/api`: FastAPI HTTP API entrypoint, routing, and dependency injection.
2. **Deterministic Gateway Layer (`gateway/`)**:
   - Central fail-closed authorization boundary. Evaluates policy, mandate constraints, cart integrity (SHA-256 cart hash), budget limits, nonces, idempotency keys, step-up requirements, and tool proxy masking.
3. **AI Agent Layer (`agent/`)**:
   - Untrusted shopping agent (LangGraph). Interprets natural language shopping intent, searches products, and constructs purchase proposals. Has ZERO direct payment authorization rights.
4. **Razorpay Integration Layer (`razorpay/`)**:
   - Official Razorpay MCP client adapter. Executes only pre-authorized execution payloads against Razorpay Test Mode.
5. **Audit Subsystem (`audit/`)**:
   - Immutable SHA-256 hash-linked audit ledger and Ed25519-signed action receipts (`action_receipt.json`) verifiable offline.
6. **Red-Team Chaos Lab (`redteam/`)**:
   - Adversarial testing suite covering prompt injection, cart tampering, nonce replay, double spend, timeout retry, expired mandates, policy violations, and unauthorized tool calls.
7. **Database Infrastructure (`db/`)**:
   - PostgreSQL models, migrations (Alembic), seeds, and atomic row locking for budget reservations.
8. **Testing Framework (`tests/`)**:
   - Cross-cutting unit, integration, security, concurrency, and end-to-end verification suites.
9. **Documentation & ADRs (`docs/`)**:
   - Architecture Decision Records (ADRs), system architecture, API contracts, security threat models, and testing strategies.
10. **Infrastructure Layer (`infra/`)**:
    - Production and container infrastructure deployment configs.

---

## Repository Structure

```text
mandate-gateway/
│
├── apps/
│   ├── web/              # Control Center frontend (Next.js)
│   └── api/              # API server (FastAPI)
│
├── gateway/              # Deterministic trust boundary & policy engine
├── agent/                # Untrusted AI shopping agent (LangGraph)
├── razorpay/             # Razorpay MCP integration rail & adapter
├── audit/                # Cryptographic audit ledger & signed receipts
├── redteam/              # Adversarial red-team chaos lab
│
├── db/                   # Database schemas, migrations, and seeds
│
├── tests/                # Verification test suites
│   ├── unit/             # Isolated component tests
│   ├── integration/      # Gateway + DB + Redis + MCP integration
│   ├── security/         # Threat model enforcement tests
│   ├── concurrency/      # Race conditions & double-spend prevention
│   └── e2e/              # End-to-end buyer-to-receipt flows
│
├── scripts/              # Developer & CI scripts
│
├── docs/                 # Documentation & Architecture Decision Records
│   ├── adr/              # Architecture Decision Records
│   ├── architecture/     # System architecture & flow diagrams
│   ├── api/              # API specs & MCP contracts
│   ├── security/         # Security design & invariants
│   └── testing/          # Testing strategy & coverage guidelines
│
├── infra/                # Infrastructure & deployment manifests
│
├── .github/
│   └── workflows/        # CI/CD automation pipelines
│
├── .env.example          # Environment configuration template
├── .gitignore            # Git exclusion rules
├── README.md             # Project documentation (this file)
├── PROJECT_CONTEXT.md    # Authoritative architectural context & source of truth
├── BUILD_STATUS.md       # Module & section engineering status tracker
├── docker-compose.yml    # Container runtime orchestration
└── Makefile              # Command interface
```

---

## Current Development Status

> **FOUNDATION STAGE (M00 — Engineering Foundation)**
>
> **Business functionality is not implemented yet.**

- **S00.1 Repository & Monorepo Architecture**: **COMPLETED**
- **S00.2 Local Development Environment**: **COMPLETED**
  - [x] **S00.2.1 Docker & Compose Foundation**: **COMPLETED**
  - [x] **S00.2.2 PostgreSQL Infrastructure**: **COMPLETED**
  - [x] **S00.2.3 Redis Infrastructure**: **COMPLETED**
  - [x] **S00.2.4 Networking & Isolation**: **COMPLETED**
  - [x] **S00.2.5 Persistent Storage & Lifecycle**: **COMPLETED**
  - [x] **S00.2.6 Developer Workflow & Local Tooling**: **COMPLETED**
  - [x] **S00.2.7 Health & Readiness Verification**: **COMPLETED**
  - [x] **S00.2.8 Foundation Verification & Freeze**: **COMPLETED**
- **S00.3 Configuration & Secrets Management**: **COMPLETE / FROZEN**
- **S00.4 Application Runtime Foundation**: **COMPLETE / FROZEN**
- **S00.5 Observability & Error Handling Foundation**: NOT STARTED
- **S00.6 Quality Gates & CI**: COMPLETE / FROZEN (`make check`, `black`, `flake8`, `mypy`, `secret_scan`, `architecture_check`, `.github/workflows/quality.yml`)
- **S00.7 Foundation Verification & Freeze**: **FINAL VERIFIED / FROZEN**

---

## Module M00 — Engineering Foundation Status

```text
============================================================
M00 — ENGINEERING FOUNDATION
STATUS: COMPLETE / FROZEN
============================================================
```

---

## Quality Gates & CI Architecture (S00.6)

Mandate Gateway enforces a fail-closed 9-step quality gate system locally (`make check`) and in GitHub Actions CI (`.github/workflows/quality.yml`).

### Developer Quality Commands
```bash
make format            # Auto-format Python source files with Black
make format-check      # Verify Black formatting compliance
make lint              # Run static code linting with Flake8
make typecheck         # Run static type checking with Mypy
make test              # Run automated unit & integration test suites
make security          # Run security test suite & secret leak prevention
make secret-scan       # Scan repository for credentials & sentinels
make architecture-check # Enforce M00 boundary invariants against premature business logic
make check             # Master Quality Gate: Run all checks sequentially (FAIL-CLOSED)
```

---

## Application Runtime Foundation (S00.4)

Mandate Gateway provides a clean, deterministic Python application runtime ([`apps/api/app/`](file:///home/santhakumar/Desktop/Raserpay/apps/api/app/)).

### Core Runtime Capabilities
1. **Deterministic Factory (`create_app`)**: Constructs standard ASGI-compliant application instances with dependency injection and zero import-time side effects (no network calls, DB, or Redis connections at import time).
2. **Lifecycle State Management (`AppLifecycle`)**: Thread-safe transitions (`BOOTING`, `INITIALIZING`, `READY`, `SHUTTING_DOWN`, `STOPPED`, `FAILED`).
3. **Health & Readiness Endpoints**:
   - `/health` (200 OK process liveness).
   - `/ready` (200 OK when application is `READY`, 503 Service Unavailable when not `READY`).
4. **Structured JSON Logging**: Standard JSON formatter with `timestamp`, `level`, `service`, `environment`, `event`, `request_id`, `correlation_id`, `trace_id`, and `SecretRedactionFilter`.
5. **Request Identity Middleware**: Sanitizes incoming `X-Request-ID`, `X-Correlation-ID`, `X-Trace-ID` or generates safe UUIDv4s.
6. **Error Boundary**: Generic exception hierarchy (`ConfigurationError`, `RuntimeInitializationError`, `DependencyInitializationError`, `RequestValidationError`, `InternalApplicationError`) redacting secrets and hiding tracebacks.

---

## Local Setup & Infrastructure Access

Local development environment orchestration is configured via Docker Compose (`docker-compose.yml`) and operated via `Makefile`.

### Developer Workflow & Local Tooling (S00.2.6)

Concise developer onboarding path:

```bash
# 1. Clone repository
git clone <repository-url>
cd mandate-gateway

# 2. Run preflight environment check (auto-creates .env from .env.example)
make preflight

# 3. Launch infrastructure containers
make dev         # or: make up

# 4. Check infrastructure health & status
make status      # or: make health

# 5. Tail infrastructure logs
make logs

# 6. Stop infrastructure containers (SAFE: preserves volume data on disk)
make down

# 7. DESTRUCTIVE RESET: Delete persistent data volumes (requires explicit confirmation)
make reset-data
```

### Health & Readiness Verification (S00.2.7)

- **PostgreSQL Health Probe**: Uses PostgreSQL-native readiness check `pg_isready -U postgres -d mandate_gateway`. Evaluates PostgreSQL process responsiveness and database accessibility.
- **Redis Health Probe**: Uses `redis-cli ping` expecting `PONG`.
- **Health vs Readiness Semantics**:
  - *Health*: Service container process is running and responding to local health checks.
  - *Readiness*: Service port (`postgres:5432` / `redis:6379`) is accepting incoming container infrastructure connections.
  - *Application Boundary*: Infrastructure probes DO NOT claim application-level business readiness; application health routes will be configured in S00.4/S00.5.

### Persistent Storage & Lifecycle (S00.2.5)

- **Storage Volume Inventory**:
  - `mandate-gateway-postgres-data`: Stateful named volume mounted at `/var/lib/postgresql/data` inside `postgres` container.
  - `mandate-gateway-redis-data`: Stateful named volume mounted at `/data` inside `redis` container.
- **Container Lifecycle & Persistence Semantics**:
  - **`docker compose stop` / `start` / `restart`**: Container state is suspended/resumed. All volume data remains 100% intact.
  - **`docker compose down` (SAFE DEFAULT)**: Container execution is stopped and bridge networks are removed, BUT named volumes are **PRESERVED** on host disk. Data survives container recreation cycles intact.
  - **`docker compose down -v` (DESTRUCTIVE RESET)**: Stops containers, removes networks, and **PERMANENTLY WIPES** all project named storage volumes. This command MUST NEVER be run automatically.
- **Safe Inspection Commands**:
  - List project volumes: `docker volume ls --filter name=mandate-gateway`
  - Inspect volume mount details: `docker volume inspect mandate-gateway-postgres-data` / `docker volume inspect mandate-gateway-redis-data`
- **Financial Correctness & Durability Boundary**:
  - Local Docker volumes provide state reproducibility across local container recreations ONLY.
  - Local Docker volumes DO NOT provide production-grade financial durability, WAL archiving, or point-in-time recovery.
  - PostgreSQL is the sole authoritative persistent datastore for financial correctness. Redis persistence (RDB snapshots) strictly supports transient caching and rate-limiting, and DOES NOT guarantee financial transaction durability.
- **Developer Reset Ownership**: Interactive reset commands (`make reset-data` with explicit user confirmation prompts) are executed safely via Makefile interface.

### Network Isolation & Trust Boundaries (S00.2.4)

- **Active Network**: `mandate-gateway-net` (User-defined Docker bridge network)
- **Host Loopback Exposure**: `127.0.0.1:5432` (PostgreSQL) and `127.0.0.1:6379` (Redis). `0.0.0.0` public network exposure is strictly forbidden.
- **Service Discovery**: Inter-container communication uses Compose DNS (`postgres:5432`, `redis:6379`). `localhost` MUST NOT be used for container-to-container communication.
- **Future Trust Model Invariant**:
  ```text
  WEB (Next.js UI) ──► API (FastAPI Gateway) ──► PostgreSQL / Redis
  WEB (Next.js UI)  ──X► PostgreSQL (Direct database access forbidden)
  WEB (Next.js UI)  ──X► Redis (Direct cache access forbidden)
  ```
  When application container runtimes are introduced, network bridge segmentation will isolate `web` from direct datastore connectivity, enforcing `api` as the sole authorized gateway boundary.

### PostgreSQL Infrastructure (S00.2.2)

- **Image Version**: `postgres:16-alpine` (Explicit, stable Alpine image)
- **Database Identity**: `mandate_gateway`
- **Development User**: `postgres` (configured via `POSTGRES_USER`)
- **Connection Hosts**:
  - **Host Machine (Developer Tools)**: `127.0.0.1:5432` (`postgresql://postgres:<password>@127.0.0.1:5432/mandate_gateway`)
  - **Docker Compose Containers**: `postgres:5432` (`postgresql://postgres:<password>@postgres:5432/mandate_gateway`)
- **Network Isolation Invariant**: `localhost` MUST NOT be used for container-to-container database communication inside Docker Compose. Inside a container, `localhost` points to the container itself, whereas container-to-container access relies on Compose bridge DNS (`postgres`).
- **Environment Requirement**: Copy `.env.example` to `.env` and set `POSTGRES_PASSWORD=CHANGE_ME_LOCAL_ONLY` (or your local development password). The canonical application `DATABASE_URL` will be established in S00.4 Application Runtime Foundation.

### Redis Infrastructure (S00.2.3)

- **Image Version**: `redis:7-alpine` (Explicit, stable Alpine image)
- **Service Identity**: `redis` (container: `mandate_gateway_redis`)
- **Connection Hosts**:
  - **Host Machine (Developer Tools)**: `127.0.0.1:6379` (`redis://127.0.0.1:6379/0`)
  - **Docker Compose Containers**: `redis:6379` (`redis://redis:6379/0`)
- **Network Isolation Invariant**: `localhost` MUST NOT be used for container-to-container Redis communication inside Docker Compose.
- **Persistence Baseline**: Standard RDB snapshotting baseline backed by stateful named volume `mandate-gateway-redis-data` mounted at `/data`.
- **Infrastructure Role**: Redis serves strictly as supporting infrastructure (ephemeral caching, transient rate-limiting). PostgreSQL is the authoritative persistent datastore for financial correctness.
- **Environment Requirement**: Copy `.env.example` to `.env`. The canonical application `REDIS_URL` will be established in S00.4 Application Runtime Foundation.

```bash
# Clone the repository
git clone <repository-url>
cd mandate-gateway

# Environment setup (S00.2 / S00.3)
cp .env.example .env

# Validate Docker Compose foundation (S00.2.1)
docker compose config

# Verify PostgreSQL Readiness (when Docker is running)
docker compose exec postgres pg_isready -U postgres -d mandate_gateway

# Verify Redis Readiness (when Docker is running)
docker compose exec redis redis-cli ping

# Install dependencies (S00.2)
make install

# Launch local services (S00.2)
make dev
```

---

## Testing Placeholder

Automated test suites and continuous integration quality gates will be configured in section **S00.6**.

```bash
# Run unit tests (S00.6)
make test

# Run code style and lint checks (S00.6)
make check
```

---

## Security Notice

> [!WARNING]
> **Foundation Stage Warning:** This repository is currently establishing engineering foundation specifications. Do not attempt to run live transactions or configure production secrets at this stage. All financial executions will run against **Razorpay Test Mode** once the integration layer is initialized.
