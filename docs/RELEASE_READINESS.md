# RAZERPAY — Release Readiness & Submission Document

## Release Profile: v1.0.0
**Project Name**: Mandate Gateway (RAZERPAY AI Commerce Agent)  
**Release Tag**: `v1.0.0`  
**Latest Verification Commit**: `efe7f942678e62f41048cd92df55c692e0650636`  
**PROJECT_CONTEXT.md SHA-256 Checksum**: `2b62d52aa707bc9bb5df60d93b04f60933562e69af8068c46cc3b6cdc2eb670a`  

---

## 1. Verification Commands & Results

| Gate / Suite | Command | Executed Status | Results |
|--------------|---------|-----------------|---------|
| **Master Quality Gate** | `make check` | **PASSED (GREEN)** | `black` clean (481 files), `flake8` clean (0 errors), `mypy` clean (0 errors across 481 files), architecture guard clean (504 files checked). |
| **Complete Unit & Integration Suite** | `PYTHONPATH=. python3 -m unittest discover -s tests -p "test_*.py"` | **PASSED** | 844 tests executed, 0 failures, 2 skipped. |
| **Chaos Failure Matrix** | `PYTHONPATH=. python3 -m unittest tests/production/test_chaos_failure_matrix.py` | **PASSED** | 15 test methods covering 18 production chaos failure scenarios passed cleanly. |
| **Secret Redaction & Leak Suite** | `PYTHONPATH=. python3 -m unittest tests/production/test_secret_redaction.py` | **PASSED** | Dict key and string Bearer token redaction verified. |
| **Production Reality Certification** | `PYTHONPATH=. python3 scripts/run_production_reality_certification.py` | **PASSED** | All 7 stages completed successfully without mock shortcuts. |
| **MCP Client Interoperability** | `PYTHONPATH=. python3 scripts/mcp_client_test_runner.py` | **PASSED** | 13 tools exposed, dangerous execution tools blocked. |

---

## 2. Security Guarantees & Non-Negotiable Invariants

### Core Invariant
> **NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE.**

### Enforced Protections
1. **Single-Use Confirmation Tokens**: Cryptographically generated via HMAC-SHA256 bound to `request_id`, `merchant_id`, `buyer_id`, and `amount_paise`. Immediately consumed upon verification; replay attempts are rejected.
2. **Deterministic Cryptographic Nonces**: DB-persisted single-use nonces at the payment execution layer.
3. **Transaction ↔ Order Binding**: 1:1 binding managed by `CommerceTransactionBindingManager`. Duplicate binding attempts raise `TransactionBindingError`.
4. **Idempotent Reconciliation**: `CommerceReconciliationEngine` tracks state transitions (`BOTH_CONFIRMED`, `PAYMENT_ONLY`, `ORDER_ONLY`, `UNRESOLVED`) with SHA-256 evidence hashing. `PAYMENT_ONLY` triggers mandatory manual review.
5. **Fail-Closed Product Truth**: Unverified product data returns `UNVERIFIED` / `SOURCE_BACKED` and blocks checkout execution.
6. **Autonomous MCP Tool Guard**: Direct execution tools (`execute_payment`, `execute_confirmed_purchase`, `create_merchant_order`) are explicitly filtered out from `tools/list` exposed to autonomous AI agents.

---

## 3. Capabilities & Reality Classification

| Domain / Component | Target Domain | Capability Level | Reality / Environment Mode | Real Money Movement? |
|--------------------|--------------|------------------|---------------------------|----------------------|
| **Public Open Commerce Catalog** | `world.openfoodfacts.org` | `VERIFIED_API` | **LIVE** | ❌ No (Catalog & Data Provenance Only) |
| **Authenticated Test Merchant** | `cafeacme.local` | `VERIFIED_API` | **SANDBOX** | ❌ No (Sandbox API Integration) |
| **Generic Web Checkout** | Any Web Domain | `CHECKOUT_HANDOFF` | **LIVE** | ❌ No (Redirect URL Generation Only) |
| **Direct Order Creation** | Real Production Merchants | `BLOCKED` | **UNSUPPORTED** | ❌ No (No Real Merchant API Keys Configured) |

---

## 4. Known Limitations & Honest Disclosures

1. **Category Scope**: Live discovery is configured against OpenFoodFacts API (grocery/food categories).
2. **Delivery & Tax Fee Truth**: Delivery and tax fees are not provided by OpenFoodFacts API and are explicitly rendered as `UNKNOWN` rather than estimated.
3. **Sandbox Merchant**: `cafeacme.local` is a local sandbox merchant endpoint requiring local DNS resolution for sandbox testing.
4. **No Real PSP Gateway Wiring**: The gateway does not connect to live production Razorpay or Stripe credentials for real monetary transactions.
5. **Development Persistence**: In default local development mode, SQLite in-process datastores are used unless Docker Compose (`docker-compose.production.yml`) with PostgreSQL/Redis is launched.

---

## 5. Deployment Prerequisites & Infrastructure

- **Runtime**: Python 3.10+
- **Containers**: Docker Compose v2.20+ (PostgreSQL 16, Redis 7, Nginx, Prometheus, Grafana)
- **Environment File**: `.env` configured from `.env.example` with valid secrets for JWT, HMAC, and Database connections.

---

## 6. Rollback Guidance

If deployment validation fails in production:
1. Trigger automatic rollback using `apps/api/deployment/rollback_manager.py` or `docker compose -f docker-compose.production.yml down`.
2. Inspect Prometheus alerts and `/health/ready` endpoint returns (503 Service Unavailable under fail-closed conditions).
3. Check the audit ledger for hash-chain continuity and Ed25519 action receipt integrity.
