# Mandate Gateway — RAZERPAY AI Commerce Agent

> **A production-grade AI commerce agent that is honestly fail-closed by design.**

[![Quality Gate](https://img.shields.io/badge/make%20check-PASSING-brightgreen)](docs/production/FINAL_TEST_CERTIFICATION.md)
[![Tests](https://img.shields.io/badge/tests-844%20passing-brightgreen)](tests/)
[![Version](https://img.shields.io/badge/version-v1.0.0-blue)](https://github.com/SanthaKumar-K-2004/mandate-gateway/releases/tag/v1.0.0)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

---

## The Problem

Every AI shopping assistant today has the same fundamental flaw: it will **invent data** to seem helpful. Invented prices, fabricated availability, made-up delivery fees — all presented as fact. When the system is wrong, the user pays for it — sometimes literally.

Worse: most AI commerce agents have **no meaningful payment safety** layer. A single LLM hallucination, a replay attack, or a duplicate request can result in double charges.

---

## The Solution

Mandate Gateway is an AI commerce agent built on a single uncompromising principle:

> **If the data is not verified, say so. If the product is unverified, block checkout. If payment confirmation is missing, do nothing.**

### Key Innovations

| Innovation | Description |
|-----------|-------------|
| **Fail-closed product truth** | Every product fact is sourced from a live API. Unverified products block checkout — no exceptions. |
| **Honest unknown disclosure** | Shipping fees, taxes, and any unverifiable cost are shown as `UNKNOWN`, never estimated. |
| **5-layer payment deduplication** | Five independent mechanisms prevent any payment effect from executing twice. |
| **Cryptographic human gate** | HMAC-SHA256 single-use tokens bind every payment confirmation to its exact request, amount, and identity. |
| **MCP security enforcement** | Direct payment and order-creation tools are **blocked** from autonomous MCP clients. |
| **Evidence-hashed audit trail** | SHA-256 evidence hashes + Ed25519 signed receipts create an immutable audit record. |
| **Real data, never synthetic** | Product discovery queries live APIs (OpenFoodFacts). No mock catalog data at runtime. |

---

## Architecture

```
User Input (Natural Language)
        │
        ▼
   AI Agent Runtime  ←→  MCP Protocol Layer (13 tools; execute_payment BLOCKED)
        │
        ▼
   Multi-Item Intent Parser → Parallel Cart Research Engine
        │
        ▼
   Live Data Providers
   ├── PublicPlatformConnector  [world.openfoodfacts.org]  LIVE / VERIFIED_API
   ├── RealPlatformConnector    [cafeacme.local]           SANDBOX / VERIFIED_API
   └── GenericWebConnector      [any merchant]             CHECKOUT_HANDOFF only
        │
        ▼
   Product Truth Engine  →  PRODUCT_VERIFIED / SOURCE_BACKED / UNVERIFIED
        │
        ▼
   Multi-Merchant Discovery → Cart Optimizer → Recommendation Engine
        │
        ▼
   Checkout Orchestrator (live re-validation → plan hash)
        │
        ▼
   ┌─ STOP: Human Confirmation Required ─────────────────────┐
   │  HMAC-SHA256 single-use token                           │
   │  All UNKNOWN fees explicitly shown                      │
   │  Human reads, confirms, submits token                   │
   └──────────────────────────────────────────────────────────┘
        │
        ▼
   Payment Safety Layer (nonce + replay + budget + step-up)
        │
        ▼
   Order Binding (1:1 cryptographic tx ↔ order)
        │
        ▼
   Reconciliation Engine → BOTH_CONFIRMED / PAYMENT_ONLY / UNRESOLVED
        │
        ▼
   Monitoring (Prometheus + Grafana + Structured Logging + Incident Engine)
```

Full architecture: [`docs/FINAL_ARCHITECTURE.md`](docs/FINAL_ARCHITECTURE.md)

---

## Safety Guarantees

### Core Invariant
> **NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE.**

Enforced by **5 independent mechanisms**:
1. HMAC-SHA256 single-use confirmation tokens (gate layer)
2. DB-persisted cryptographic nonces (execution layer)
3. Replay fingerprint rejection (request layer)
4. 1:1 transaction ↔ order binding with duplicate rejection (binding layer)
5. Idempotent reconciliation with evidence hashing (reconciliation layer)

### Security Properties
- Secret redaction in all log output
- Webhook HMAC-SHA256 verification + timestamp expiry
- Autonomous MCP clients cannot invoke `execute_payment` or `create_merchant_order`
- Budget enforcement before any payment authorization
- Step-up challenge for high-value transactions
- Ed25519-signed action receipts (offline-verifiable)
- SHA-256 cryptographic audit ledger hash-chain

---

## Live Data Integrations

| Integration | What Is Genuinely Live |
|-------------|----------------------|
| `world.openfoodfacts.org` | Real HTTP API — real food/grocery product data |
| All algorithmic layers | Cart research, optimization, recommendation — run on real data |
| Safety mechanisms | All confirmation, deduplication, reconciliation — real enforcement |
| Prometheus `/metrics` | Real metrics scrape endpoint |

| What Is NOT Live (Honest) |
|--------------------------|
| Real money / PSP (no Razorpay/Stripe credentials wired) |
| Real merchant order creation (sandbox `cafeacme.local` only) |
| Delivery fees / taxes (shown as `UNKNOWN` — not estimatable) |

---

## Capability Matrix

| Capability | Level | Notes |
|-----------|-------|-------|
| Food product discovery | ✅ LIVE | OpenFoodFacts public API |
| Price truth verification | ✅ LIVE | Against live source |
| Multi-merchant comparison | ✅ LIVE | Across registered connectors |
| Multi-item cart optimization | ✅ LIVE (algorithmic) | Branch-and-bound |
| Explainable recommendations | ✅ LIVE (algorithmic) | Multi-factor scored |
| Human confirmation gate | ✅ LIVE | HMAC-SHA256, single-use |
| Payment execution | ⚠️ SANDBOX ONLY | `cafeacme.local` test merchant |
| Real merchant checkout | ✅ HANDOFF | URL generation — no direct API |
| Delivery/tax fees | ⚠️ UNKNOWN | Honestly disclosed, never estimated |
| Real PSP integration | ❌ NOT AVAILABLE | No live payment credentials |

Full matrix: [`docs/FINAL_CAPABILITY_MATRIX.md`](docs/FINAL_CAPABILITY_MATRIX.md)

---

## Quick Start

### Prerequisites
- Python 3.10+
- Docker + Docker Compose (for infrastructure)

### Setup

```bash
# Clone
git clone https://github.com/SanthaKumar-K-2004/mandate-gateway.git
cd mandate-gateway

# Environment
cp .env.example .env

# Install dependencies
make install

# Verify quality gate (must be GREEN before anything else)
make check
# Expected: [✓] ALL S00.6 QUALITY GATE CHECKS PASSED CLEANLY!
```

### Run Infrastructure (optional — for full persistence)

```bash
make dev        # Start PostgreSQL + Redis
make status     # Verify health
```

### Run the Production Reality Certification

```bash
PYTHONPATH=. python3 scripts/run_production_reality_certification.py
# Expected: [✓] PRODUCTION REALITY CERTIFICATION COMPLETED SUCCESSFULLY!
```

### Run Live Cart Research Demo

```bash
PYTHONPATH=. python3 scripts/run_live_cart_research_pilot.py
# Queries live OpenFoodFacts API for real products
```

---

## Testing

```bash
# Full quality gate (black + flake8 + mypy + tests + secret scan + architecture guard)
make check

# All 844 tests
PYTHONPATH=. python3 -m unittest discover -s tests -p "test_*.py"

# Production chaos failure matrix (18 scenarios)
PYTHONPATH=. python3 -m unittest tests/production/test_chaos_failure_matrix.py -v

# Secret redaction enforcement
PYTHONPATH=. python3 -m unittest tests/production/test_secret_redaction.py -v

# MCP client interoperability
PYTHONPATH=. python3 scripts/mcp_client_test_runner.py
```

**Test results: 844 tests, 0 failures, 2 skipped. Black clean. Flake8 clean. MyPy 0 errors.**

---

## Project Structure

```
mandate-gateway/
├── apps/api/
│   ├── agent/          # AI agent runtime, MCP server, tool registry, confirmation gate
│   ├── commerce/       # Product truth, connectors, cart research, reconciliation
│   │   ├── connectors/ # PublicPlatformConnector, RealPlatformConnector, GenericWeb
│   │   ├── product_truth_engine.py
│   │   ├── cart_research.py
│   │   ├── cart_optimizer.py
│   │   ├── recommendation_engine.py
│   │   ├── transaction_binding.py
│   │   └── reconciliation.py
│   ├── domain/         # Authorization, mandate, budget, nonce, step-up, execution
│   ├── observability/  # Prometheus exporter, structured logger, incident engine
│   ├── routers/        # FastAPI HTTP endpoints
│   └── config/         # Settings, production validator
├── tests/
│   ├── unit/           # Component-level tests
│   ├── integration/    # End-to-end DB + API tests
│   ├── security/       # Threat model enforcement
│   ├── commerce/       # Cart, product truth, connector tests
│   └── production/     # Chaos matrix, secret redaction, smoke tests
├── scripts/            # Demo, certification, and MCP test scripts
├── docs/
│   ├── FINAL_ARCHITECTURE.md
│   ├── FINAL_CAPABILITY_MATRIX.md
│   ├── FINAL_DEMO_SCRIPT.md
│   └── production/     # Deployment guide, runbook, incident response
├── infra/
│   ├── nginx/          # Reverse proxy with rate limiting
│   ├── prometheus/     # Metrics and alerting rules
│   └── grafana/        # 5 production dashboards
├── docker-compose.production.yml
├── Makefile
├── .env.example
└── PROJECT_CONTEXT.md  # Authoritative architectural context (DO NOT MODIFY)
```

---

## Roadmap

| Milestone | Status | Description |
|-----------|--------|-------------|
| M00 — Engineering Foundation | ✅ COMPLETE | Repo, CI, config, runtime, observability |
| M01–M05 — Mandate Domain | ✅ COMPLETE | Authorization, execution, persistence, audit |
| M23 — Real-Data AI Discovery | ✅ COMPLETE | Live OpenFoodFacts integration, fail-closed |
| M24 — Product Truth Engine | ✅ COMPLETE | Evidence-hashed verification |
| M25 — Order/Payment Binding | ✅ COMPLETE | Cryptographic 1:1 binding, webhooks |
| M26 — Production Reality | ✅ COMPLETE | Connector classification, reconciliation |
| M27 — Multi-Merchant Network | ✅ COMPLETE | Multi-source discovery, comparison |
| M28 — Cart Intelligence | ✅ COMPLETE | Multi-item research, optimizer, recommendations |
| M29 — Production Release | ✅ COMPLETE | Docker, Nginx, Prometheus, Grafana, chaos tests |
| **v1.0.0 Release** | ✅ **TAGGED** | Final certified release |

---

## Security Notice

> [!IMPORTANT]
> **This system enforces fail-closed safety at every layer.** Unverified products block checkout. Duplicate payment attempts are rejected. Dangerous MCP tools are excluded from autonomous client access. Secret values are redacted from all log output.

> [!WARNING]
> **No real payment credentials are configured.** Payment execution operates in sandbox mode only (`cafeacme.local`). To use with a real PSP, add appropriate API credentials to `.env` and integrate a real payment provider connector.

---

## Known Limitations

- Food/grocery products only (OpenFoodFacts scope)
- No real PSP credentials — sandbox payment execution only
- Delivery fees and taxes always shown as `UNKNOWN`
- `cafeacme.local` requires local DNS or hosts file entry
- SQLite in development; PostgreSQL required for production persistence

---

## License

MIT License — see [LICENSE](LICENSE)

---

## Demo

Full demo script with exact commands and expected outputs: [`docs/FINAL_DEMO_SCRIPT.md`](docs/FINAL_DEMO_SCRIPT.md)

```bash
# 30-second proof of safety guarantees
PYTHONPATH=. python3 scripts/run_production_reality_certification.py
```
