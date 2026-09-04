# Mandate Gateway — Release Readiness Document

## Release Profile
**Project Name**: Mandate Gateway (AI Commerce Safety Agent)  
**Public Branding**: Mandate Gateway — Verified AI Commerce Agent  
**Release Target**: `v2.0.0` (Agentic Payment Protocol & Razorpay Test Integration Release)
**PROJECT_CONTEXT.md SHA-256 Checksum**: `2b62d52aa707bc9bb5df60d93b04f60933562e69af8068c46cc3b6cdc2eb670a`  

> **Disclaimer Notice**: Mandate Gateway is an independent open-source AI commerce safety project. It is **NOT** affiliated with, endorsed by, or connected to **Razorpay Software Private Limited**.

---

## 1. Master Verification Accounting

### Authoritative Primary Test Suite
```bash
PYTHONPATH=. python3 -m unittest discover -s tests -p "test_*.py"
```
- **Tests Executed**: **870**
- **Passed**: 868
- **Skipped**: 2 (Environment-specific integration skips)
- **Failed**: 0
- **Errors**: 0

### Security & Protocol Test Suites
```bash
PYTHONPATH=. python3 -m unittest discover -s tests/security -p "test_*.py"
```
- **Security Tests Executed**: **281**
- **Passed**: 281
- **Failed**: 0

### Targeted Certification Suites
- **Production Chaos Matrix**: 18 test methods covering production chaos failure scenarios passed.
- **Secret Redaction Suite**: Verifies zero secret leaks in repr/logs/exceptions passed.
- **Production Reality Certification**: 7 / 7 stages passed (`scripts/run_production_reality_certification.py`).
- **MCP Client Interoperability Suite**: 5 / 5 steps passed (`scripts/mcp_client_test_runner.py`).

---

## 2. Core Security Invariant & Defense-in-Depth Controls

### Non-Negotiable Invariant
> **NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE.**

### Defense-in-Depth Across Five Enforcement Layers
1. **Gate Layer**: HMAC-SHA256 single-use confirmation tokens bound to `request_id`, `merchant_id`, `buyer_id`, and `amount_paise`. Consumed atomically; replay attempts raise `ConfirmationError`.
2. **Execution Layer**: Single-use cryptographic nonces persisted in database with atomic consumption.
3. **Request Layer**: Cryptographic request fingerprinting preventing identical payload replay.
4. **Binding Layer**: 1:1 transaction ↔ order binding enforced by `CommerceTransactionBindingManager`. Rebind attempts raise `TransactionBindingError`.
5. **Reconciliation Layer**: Idempotent reconciliation engine (`CommerceReconciliationEngine`) tracking ledger states (`BOTH_CONFIRMED`, `PAYMENT_ONLY`, `ORDER_ONLY`, `UNRESOLVED`). `PAYMENT_ONLY` triggers mandatory manual review.

---

## 3. Autonomous MCP Execution Barrier

Direct payment and order creation tools (`execute_payment`, `execute_confirmed_purchase`, `create_merchant_order`) are subject to a **dual execution barrier**:
- **Discovery Filter**: Excluded from MCP `tools/list` JSON-RPC response.
- **Invocation Barrier**: Explicitly checked and rejected in `tools/call` JSON-RPC handler, returning JSON-RPC error code `-32000` (`Security Rejection: Tool is restricted`).

---

## 4. Realistic Reality Classification Matrix

Mandate Gateway distinguishes live, sandbox, and handoff capabilities explicitly and does not classify sandbox data as real merchant commerce.

| Provider / Connector | Target Domain | Capability Classification | Mode | Real Money Movement? |
|----------------------|--------------|---------------------------|------|----------------------|
| `PublicPlatformConnector` | `world.openfoodfacts.org` | `LIVE_CATALOG_API` | **LIVE** | ❌ No (Live Product Intelligence API) |
| `RazorpayClient` (Test) | `https://api.razorpay.com/v1` | `TEST / SANDBOX` | **TEST** | ❌ No (Official Razorpay Test API) |
| `RazorpayClient` (Live) | `https://api.razorpay.com/v1` | `NOT AVAILABLE` | **LIVE** | 🔴 Disabled (Requires Production Keys) |
| `X402PaymentAdapter` | HTTP `402 Payment Required` | `PROTOCOL_COMPATIBLE` | **PROTOCOL_ADAPTER** | ❌ No (Protocol Proof Layer) |
| `UAPAuthorizationLayer` | Internal Delegated Tokens | `UAP_ALIGNED` | **AUTHORIZATION** | ❌ No (Policy & Delegation Engine) |
| `RealPlatformConnector` | `cafeacme.local` | `VERIFIED_API` | **SANDBOX** | ❌ No (Authenticated Sandbox API) |
| `GenericWebCheckoutConnector` | Validated HTTPS Merchant URLs | `CHECKOUT_HANDOFF` | **LIVE** | ❌ No (Redirect Handoff URL Only) |

---

## 5. Honest Disclosures & Limitations

1. **Catalog Scope**: Live discovery is configured against OpenFoodFacts API (grocery and food products).
2. **Delivery & Tax Fee Truth**: Shipping and tax fees are unavailable via public catalog APIs and are explicitly rendered as `UNKNOWN` rather than estimated.
3. **Razorpay Test Mode**: `RAZORPAY_MODE=test` is active by default; real money is never moved without explicit production setup.
4. **Protocol Adapters**: x402 and UAP layers operate as standard-aligned architectural adapters within Mandate Gateway's safety boundary.
5. **Development Persistence**: In default local development mode, SQLite in-process datastores are used unless Docker Compose (`docker-compose.production.yml`) with PostgreSQL/Redis is launched.


---

## 6. Deployment Prerequisites & Rollback

- **Runtime**: Python 3.10+
- **Containers**: Docker Compose v2.20+ (PostgreSQL 16, Redis 7, Nginx, Prometheus, Grafana)
- **CI Pipeline**: GitHub Actions (`.github/workflows/ci.yml`) executing `make check`.
- **Rollback**: Trigger rollback via `apps/api/deployment/rollback_manager.py` or `docker compose -f docker-compose.production.yml down`.
