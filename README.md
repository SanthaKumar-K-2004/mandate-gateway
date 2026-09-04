# RAZERPAY — Mandate Gateway
### Autonomous AI Commerce Trust & Payment Safety Protocol

[![Buildathon Track](https://img.shields.io/badge/Razorpay_Raze_Buildathon_2026-Autonomous_AI_Commerce_&_Agent_Payment_Protocols-0052CC?style=for-the-badge&logo=razorpay)](https://github.com/SanthaKumar-K-2004/mandate-gateway)
[![Current Release](https://img.shields.io/badge/Current_Release-v1.5.0-blue?style=for-the-badge)](file:///home/santhakumar/Desktop/Razorpay/docs/RELEASE_READINESS.md)
[![Commit SHA](https://img.shields.io/badge/Commit-836de91-informational?style=for-the-badge)](https://github.com/SanthaKumar-K-2004/mandate-gateway/commit/836de91)
[![Test Suite](https://img.shields.io/badge/Test_Suite-275_PASSED_/_100%25-brightgreen?style=for-the-badge)](file:///home/santhakumar/Desktop/Razorpay/docs/FINAL_SUBMISSION_ACCEPTANCE_TEST.md)
[![Security Gate](https://img.shields.io/badge/Security_Guard-869_Files_Scanned_/_0_Leaks-success?style=for-the-badge)](file:///home/santhakumar/Desktop/Razorpay/SECURITY.md)

---

> **DISCLAIMER & HACKATHON ENTRY NOTICE**
> **RAZERPAY — Mandate Gateway** is an independent open-source research and engineering submission built by **SanthaKumar K** ([@SanthaKumar-K-2004](https://github.com/SanthaKumar-K-2004)) for the **Razorpay Raze Buildathon 2026** under the *Autonomous AI Commerce & Agent Payment Protocols* track. It is not an official product of, nor is it endorsed by, Razorpay Software Private Limited.

---

## ⚡ Judge in 60 Seconds

* **The Problem:** Autonomous AI agents that shop or make financial decisions tend to hallucinate product specs, treat unverified shipping/tax as ₹0, ignore velocity limits, and execute transactions without single-use authorization—creating high financial and operational risk.
* **The Solution:** **Mandate Gateway** provides an architectural trust layer between LLM decision engines and commerce backends. It decouples product research from payment authorization, enforces strict multi-item cart optimization, and wraps execution in a fail-closed, cryptographically bound safety pipeline.
* **Live Proof:** Live HTTP requests to the **OpenFoodFacts REST API** for multi-item product research, SHA-256 evidence hashing, deterministic budget evaluation, and zero false certainty on unknown fees.
* **Safety Proof:** HMAC-SHA256 single-use confirmation tokens, DB-persisted execution nonces, replay protection, 1:1 transaction-order binding, and idempotent state reconciliation.
* **Honest Boundary:** Live API product research and algorithmic optimization are fully operational. No live production real-money PSP credentials (Razorpay/Stripe) are configured; payment execution is safely demonstrated via local sandbox (`cafeacme.local`) and validated HTTPS checkout handoff.

---

## 🎯 What Is Razerpay Mandate Gateway?

**RAZERPAY** is a safety-first AI commerce system that turns natural-language shopping requests into **verified product research, multi-item cart optimization, explainable recommendations, and controlled checkout workflows**.

The system is designed around one non-negotiable principle:

> **NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE.**

Instead of allowing an AI agent to directly control payment or ordering, RAZERPAY separates **AI reasoning and commerce research** from **high-risk financial execution**.

```
       NO VERIFIED EVIDENCE  ──►  NO FALSE CERTAINTY
     NO HUMAN CONFIRMATION  ──►  NO PAYMENT EFFECT
    NO SAFE EXECUTION PATH  ──►  FAIL CLOSED
```

---

## 🚩 Project Track & Focus Areas

**Track: Autonomous AI Commerce & Agent Payment Protocols (Razorpay Raze Buildathon 2026)**

RAZERPAY focuses on the intersection of:
* AI agents
* Autonomous commerce research
* Multi-item shopping
* Payment safety
* Human-in-the-loop authorization
* MCP tool security
* Transaction idempotency
* Commerce reconciliation
* Explainable recommendations

The system is intentionally designed so that an AI agent can **research and recommend**, while sensitive financial actions remain behind explicit safety boundaries.

---

## 1. The Problem

AI agents can already understand requests such as:
> *"Find me coffee and biscuits under ₹300."*

But turning that request into a trustworthy commerce workflow introduces several difficult problems:

### AI agents can make mistakes
An agent may:
* misunderstand the requested items
* select the wrong product
* use stale or incomplete product information
* combine incompatible products
* exceed the user's budget
* trust an unsafe checkout URL
* attempt the same payment more than once
* act on unverified product information

### Payment systems have a different risk profile
A wrong recommendation is inconvenient.
A duplicated payment is a financial incident.

Therefore, commerce agents need a strict boundary between:
$$\text{Reasoning} \longrightarrow \text{Recommendation} \longrightarrow \text{Authorization} \longrightarrow \text{Execution} \longrightarrow \text{Reconciliation}$$

RAZERPAY is built around that boundary.

---

## 2. The Solution

RAZERPAY provides an end-to-end AI commerce workflow:

```text
Natural-Language Request
          │
          ▼
   Intent Extraction
          │
          ▼
   Live Product Research (OpenFoodFacts API)
          │
          ▼
 Product Truth Verification (SHA-256 Provenance)
          │
          ▼
 Multi-Item Cart Optimization (Deterministic Search)
          │
          ▼
 Explainable Recommendation
          │
          ▼
 Total-Cost Truth Check (UNKNOWN ≠ ₹0)
          │
          ▼
 Human Confirmation Gate (HMAC-SHA256 Single-Use Token)
          │
          ▼
 Controlled Checkout / Handoff
          │
          ▼
 Payment & Order Binding (1:1 Strict Ratio)
          │
          ▼
 Idempotent Reconciliation (DB Nonce & Bloom Fingerprint)
          │
          ▼
 Cryptographic Audit Trail (Immutable Ledger)
```

The AI does not receive unrestricted payment authority.

---

## 3. Real-World Example

A user can submit:
```text
Find coffee and biscuits under ₹300
```

RAZERPAY extracts:
```text
Items:
  • Coffee × 1
  • Biscuits × 1

Budget:
  ₹300 INR

Strategy:
  Best Value
```

The system then researches available candidates via live OpenFoodFacts API, evaluates product evidence, searches combinations, and produces an explainable recommendation.

A result contains:
```text
Requested items:       2
Candidates researched: 6
Cart combinations:     9
Feasible carts:        1

Known product subtotal: ₹285
Remaining budget:       ₹15

Shipping:               UNKNOWN
Tax:                    UNKNOWN

Merchant count:         1
Checkout:               CHECKOUT_HANDOFF
```

Importantly:
> **UNKNOWN fees are never silently treated as ₹0.**

If shipping or tax cannot be verified via API, the system explicitly marks them as `UNKNOWN`.

---

## 4. What Is Actually Live? (Reality Matrix)

RAZERPAY deliberately distinguishes between real external integrations, sandbox environments, and checkout handoffs.

| Capability / Feature | Reality / Status | Implementation Details |
| :--- | :---: | :--- |
| **OpenFoodFacts Product Discovery** | 🟢 LIVE | HTTP GET to OpenFoodFacts REST API (`world.openfoodfacts.org`) |
| **External Product Requests** | 🟢 LIVE | Real-time payload extraction, price parsing, ingredient verification |
| **Product Provenance & Hashing** | 🟢 LIVE | SHA-256 hashing of raw API responses and product metadata |
| **Multi-Item Research & Parsing** | 🟢 LIVE | Parses complex multi-item goals and target budget limits |
| **Cart Optimization** | 🟢 LIVE / Algorithmic | Deterministic combination search maximizing utility under budget |
| **Explainable Recommendation** | 🟢 LIVE / Algorithmic | Explicit scoring breakdown (budget fit, merchant count, subtotal, evidence) |
| **Checkout URL Handoff** | 🟢 LIVE / Handoff | Validates destination URLs and returns secure browser handoff link |
| **Human Confirmation Gate** | 🟢 ENFORCED | HMAC-SHA256 signed single-use authorization token required |
| **Webhook Signature Verification** | 🟢 LIVE | Cryptographic signature checking for merchant event streams |
| **Reconciliation Engine** | 🟢 LIVE / Algorithmic | Idempotent state reconciliation (`PAYMENT_ONLY`, `BOTH_CONFIRMED`) |
| **Prometheus Metrics & Health** | 🟢 LIVE | `/metrics`, `/health`, `/readiness` operational endpoints |
| **Cafe Acme Sandbox Merchant** | 🟡 SANDBOX | Local mock merchant execution engine (`cafeacme.local`) |
| **Direct Real-Money Payment** | 🔴 NOT ENABLED | No production PSP credentials (Razorpay/Stripe) loaded |
| **Production Merchant Order APIs** | 🔴 NOT SUPPORTED | Relies on OpenFoodFacts public catalog data and sandbox merchant |
| **Delivery / Tax Verification** | 🟡 UNKNOWN | Explicitly marked `UNKNOWN` when unavailable via catalog API |

---

## 5. Product Truth Classification

Every product candidate is classified according to the quality of its evidence:

| Status | Meaning | Action |
| :--- | :--- | :--- |
| `PRODUCT_VERIFIED` | SKU, price, image URL, and availability confirmed via live API | Eligible for Cart Optimization |
| `SOURCE_BACKED` | Valid source payload, but secondary fields (e.g., nutrition/shipping) missing | Eligible for Cart Optimization |
| `UNVERIFIED` | Product information could not be sufficiently confirmed from live API | Checkout Blocked |

The system follows a fail-closed rule:
```text
UNVERIFIED candidate  ──►  Checkout Blocked
```

This prevents an AI agent from converting uncertain product information into an unsafe transaction.

---

## 6. Multi-Item Cart Intelligence

RAZERPAY does not treat a shopping request as a single-product search.

For `coffee + biscuits`, the system:
1. parses individual shopping requirements,
2. researches multiple candidates in parallel,
3. normalizes candidate evidence,
4. removes duplicate items,
5. evaluates merchant combinations,
6. enforces spending mandate budget constraints,
7. optimizes the complete multi-item cart,
8. calculates known subtotal costs,
9. identifies unknown costs,
10. explains why a specific cart was selected.

The optimizer uses deterministic bounded search rather than allowing an LLM to arbitrarily invent a final cart.

---

## 7. Explainable Recommendations

Recommendations are generated using explicit scoring factors rather than an unexplained AI decision:

The recommendation layer considers factors such as:
* product evidence score
* item price
* budget fit
* item coverage ratio
* merchant count
* checkout capability
* verification status
* known versus unknown costs

Example output shown in UI:
```text
Why this cart?

✓ All requested items found (Coffee + Biscuits)
✓ Product evidence verified (SHA-256 hashed payload)
✓ Within known budget (₹285 / ₹300 limit)
✓ Fewer merchants required (Single merchant handoff)
✓ Secure checkout handoff available
⚠ Shipping/tax remain UNKNOWN (Flagged for human confirmation)
```

---

## 8. Total-Cost Truth

One of the core design principles is:

> **UNKNOWN ≠ ₹0**

If the system knows:
$$\text{Product Subtotal} = ₹280$$

but cannot verify:
$$\text{Shipping} = ?, \quad \text{Tax} = ?$$

it does **NOT** report:
$$\text{Total} = ₹280 \quad \text{(FALSE CERTAINTY)}$$

Instead, it outputs:
```text
Known subtotal: ₹280

Shipping: UNKNOWN
Tax:      UNKNOWN

Fully verified total: NO
```

This prevents false certainty in AI-generated commerce decisions.

---

## 9. Safety Architecture

The payment boundary is intentionally separated from the AI research layer:

```text
┌─────────────────────────────────────────────────────────────┐
│                       AI / MCP AGENT                        │
│                                                             │
│  Intent Extraction · Research · Comparison · Recommendation │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ Restricted Boundary
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    HUMAN CONFIRMATION                       │
│                                                             │
│     HMAC-SHA256 single-use authorization token gate        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    TRANSACTION SAFETY                       │
│                                                             │
│ Idempotency · Nonce · Replay Protection · Binding · Budget │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     EXECUTION LAYER                         │
│                                                             │
│     Sandbox (cafeacme.local) / Validated Checkout Handoff   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     RECONCILIATION                          │
│                                                             │
│ Payment ↔ Order · Evidence Hashing · Manual Review · Ledger │
└──────────────────────────────┬──────────────────────────────┘
```

---

## 10. Core Payment Safety Invariant (5-Layer Model)

The central invariant is:

> **NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE.**

RAZERPAY enforces a 5-layer defense-in-depth model:

1. **Single-Use Confirmation Tokens (Layer 1):** HMAC-SHA256 signed tokens cryptographically bound to transaction context (`request_id`, `amount`, `merchant`, `buyer`). Once consumed, token reuse is rejected.
2. **Atomic Execution Nonces (Layer 2):** Database-persisted single-use nonces transition state atomically.
3. **Request Replay Protection (Layer 3):** SHA-256 fingerprinting catches duplicate HTTP requests instantly.
4. **Transaction ↔ Order Binding (Layer 4):** Payment operations bind 1:1 with specific merchant order structures.
5. **Idempotent Reconciliation Engine (Layer 5):** Payment and order states are reconciled explicitly:
   * `BOTH_CONFIRMED`
   * `PAYMENT_ONLY` (Requires manual review rather than silent retry)
   * `ORDER_ONLY`
   * `UNRESOLVED`

---

## 11. Model Context Protocol (MCP) Security Boundary

RAZERPAY exposes powerful commerce tools through MCP while restricting dangerous autonomous actions.

### Exposed Read / Research Tools
* `search_products`: Queries live OpenFoodFacts API for items matching query.
* `get_product_details`: Retrieves deep product evidence and metadata.
* `compare_products`: Compares multiple candidate products.
* `recommend_product`: Generates explainable cart recommendations.
* `research_shopping_request`: Executes full intent-to-research pipeline.
* `optimize_cart`: Algorithmic combination search for multi-item requests.
* `get_checkout_capability`: Inspects available checkout handoff paths.
* `get_connector_health`: Audits operational status of connectors.
* `create_purchase_plan`: Prepares candidate purchase plan for human review.
* `get_budget_status`: Checks active mandate budget limits.
* `get_transaction_status`: Queries security and transaction states.
* `get_purchase_status`: Audits purchase plan execution lifecycle.
* `reconcile_commerce_operation`: Triggers reconciliation evaluation.

### Restricted / Blocked Execution Tools
Direct financial or merchant execution tools are **blocked from autonomous MCP discovery**:
* `execute_payment`
* `create_merchant_order`
* `execute_confirmed_purchase`

This creates a critical architectural distinction:
$$\text{AI can reason about commerce} \quad \neq \quad \text{AI automatically controls money}$$

---

## 12. Security Controls Summary

| Security Control | Status | Technical Implementation |
| :--- | :---: | :--- |
| **Single-Use Confirmation** | Enforced | HMAC-SHA256 signed token with expiration timestamp |
| **HMAC Authorization Gate** | Enforced | Single-use consumption flag in persistent database |
| **Transaction Idempotency** | Enforced | Idempotency key tracking on API gateway and router |
| **Replay Protection** | Enforced | SHA-256 request payload fingerprint bloom barrier |
| **1:1 Transaction/Order Binding** | Enforced | Strict foreign-key binding between payment ID & order ID |
| **Webhook Signature Validation** | Enforced | Secret-based HMAC verification on inbound events |
| **Timestamp Validation** | Enforced | ±300s drift window check on authorization requests |
| **Secret Redaction Filter** | Enforced | Auto-redacts bearer tokens, API keys, and authorization headers |
| **Autonomous Payment-Tool Blocking**| Enforced | Public MCP tool list filters out execution primitives |
| **Fail-Closed Product Truth** | Enforced | `UNVERIFIED` candidates immediately block execution |
| **Budget Mandate Enforcement** | Enforced | Daily, category, and velocity limits evaluated pre-checkout |
| **Cryptographic Audit Trail** | Enforced | SHA-256 evidence chain stored in immutable audit ledger |
| **Reconciliation Engine** | Enforced | Explicit state machine handling `PAYMENT_ONLY` edge cases |
| **SSRF-Safe Checkout Validation** | Enforced | Target URL domain whitelist and scheme restriction |

---

## 13. Checkout Security & SSRF Protection

The generic web checkout connector does not blindly redirect to arbitrary URLs.

Checkout destinations are validated against dangerous destinations and schemes. The system rejects unsafe targets such as:
* `localhost`
* `127.0.0.1`
* `169.254.169.254`
* `file:`
* `javascript:`
* `data:`

The resulting capability is `CHECKOUT_HANDOFF` rather than `AUTONOMOUS_PURCHASE`.

---

## 14. Full System Architecture Diagram

```text
                                USER
                                 │
                                 ▼
                      ┌────────────────────┐
                      │  AI / Agent Layer   │
                      │                    │
                      │ Intent Extraction  │
                      │ Planning           │
                      │ Research           │
                      └─────────┬──────────┘
                                │
                                ▼
                      ┌────────────────────┐
                      │     MCP Layer      │
                      │                    │
                      │ Commerce Tools     │
                      │ Safety Filtering   │
                      └─────────┬──────────┘
                                │
                   ┌────────────┼─────────────┐
                   ▼            ▼             ▼
             Product Truth   Cart Engine   Recommendation
                   │            │             │
                   └────────────┼─────────────┘
                                ▼
                       ┌──────────────────┐
                       │ Total Cost Truth  │
                       └────────┬─────────┘
                                ▼
                       ┌──────────────────┐
                       │ Confirmation Gate│
                       └────────┬─────────┘
                                ▼
                       ┌──────────────────┐
                       │ Execution Safety │
                       └────────┬─────────┘
                                ▼
                       ┌──────────────────┐
                       │ Reconciliation   │
                       └────────┬─────────┘
                                ▼
                       ┌──────────────────┐
                       │ Audit + Metrics  │
                       └──────────────────┘
```

Complete architecture specification is available in [`docs/FINAL_ARCHITECTURE.md`](file:///home/santhakumar/Desktop/Razorpay/docs/FINAL_ARCHITECTURE.md).

---

## 15. External Commerce Integrations

### OpenFoodFacts (`world.openfoodfacts.org`)
Used for live public product discovery and product evidence retrieval. The integration is treated as a **catalog/data source**, not a payment processor. Merchant-specific price, inventory, shipping, and tax information is not assumed when unavailable.

### Cafe Acme (`cafeacme.local`)
Provides the controlled sandbox merchant environment used for testing transaction and commerce execution flows. It is a local testing simulation.

### Generic Web Checkout Connector
Provides a controlled handoff mechanism to web merchants. Generates a validated checkout destination URL rather than executing autonomous background orders.

---

## 16. Full-Stack Web Interface (`apps/web`)

Built with Next.js 14, Tailwind CSS, Lucide icons, and Apple SF Pro / Microsoft Fluent Design glassmorphism aesthetics.

| Route | Purpose | Key Components |
| :--- | :--- | :--- |
| [`/`](file:///home/santhakumar/Desktop/Razorpay/apps/web/app/page.tsx) | **Command Hub** | System status, metrics, quick launch navigation |
| [`/buyer`](file:///home/santhakumar/Desktop/Razorpay/apps/web/app/buyer/page.tsx) | **Live Agent Research** | Natural-language query input, live OpenFoodFacts API telemetry, cart optimizer |
| [`/mandates`](file:///home/santhakumar/Desktop/Razorpay/apps/web/app/mandates/page.tsx) | **Policy Engine** | Spending mandate creation, category velocity limits |
| [`/transactions`](file:///home/santhakumar/Desktop/Razorpay/apps/web/app/transactions/page.tsx) | **Security & Safety** | Live 5-layer security state, HMAC verification modal |
| [`/merchant`](file:///home/santhakumar/Desktop/Razorpay/apps/web/app/merchant/page.tsx) | **Merchant Sandbox** | `cafeacme.local` simulation state, order verification |
| [`/audit`](file:///home/santhakumar/Desktop/Razorpay/apps/web/app/audit/page.tsx) | **Cryptographic Audit** | Immutable ledger view, SHA-256 evidence chain inspection |
| [`/red-team`](file:///home/santhakumar/Desktop/Razorpay/apps/web/app/red-team/page.tsx) | **Security Testing** | Interactive security suite simulating replay attacks & budget breaches |

---

## 17. Observability & Telemetry

* **Health Endpoints:** `/health`, `/health/liveness`, `/health/readiness`
* **Prometheus Metrics:** `/metrics` exposing API response latencies, tool calls, and reconciliation counters
* **Structured Application Logging:** JSON-formatted logs with request ID, correlation ID, and trace context
* **Cryptographic Audit Ledger:** SHA-256 evidence chain indexing all transaction authorizations

---

## 18. Repository Structure

```text
RAZERPAY/
├── apps/
│   ├── api/                  # FastAPI Backend API & MCP Server
│   │   ├── agent/            # Intent Parsing & Optimization Logic
│   │   ├── commerce/         # OpenFoodFacts & Sandbox Connectors
│   │   ├── deployment/       # Production Factory & Health Routers
│   │   └── routers/          # REST API Endpoints
│   └── web/                  # Next.js 14 Glassmorphism Web App
├── docs/                     # Submission Specifications & Verification Logs
│   ├── FINAL_ARCHITECTURE.md
│   ├── FINAL_CAPABILITY_MATRIX.md
│   ├── FINAL_DEMO_SCRIPT.md
│   ├── RELEASE_READINESS.md
│   └── FINAL_SUBMISSION_ACCEPTANCE_TEST.md
├── scripts/                  # Certification & Runner Scripts
│   ├── mcp_client_test_runner.py
│   ├── run_live_cart_research_pilot.py
│   └── run_production_reality_certification.py
├── tests/                    # Pytest Comprehensive Test Suite (275 tests)
├── docker-compose.production.yml
├── Makefile                  # Quality Gate Automation
├── PROJECT_CONTEXT.md        # Core Invariant Governance Matrix
└── README.md                 # Primary Submission Landing Page
```

---

## 19. Quick Start & Setup Guide

### Prerequisites
* Python 3.11+
* Node.js 18+ & `npm`
* `make` build utility

### 1. Clone Repository & Setup Environment
```bash
git clone https://github.com/SanthaKumar-K-2004/mandate-gateway.git
cd mandate-gateway

# Set up Python virtual environment & backend dependencies
python3.11 -m venv .venv311
source .venv311/bin/activate
make install

# Install Frontend dependencies
cd apps/web
npm install
cd ../..
```

### 2. Environment Configuration
```bash
cp .env.example .env
```

---

## 20. Run the Quality Gate

The primary verification command is:
```bash
make check
```

This automated pipeline executes:
* Formatting & Code Style Check (`ruff`)
* Type Checking (`mypy`)
* Architecture Layer Violation Guard (`scripts/architecture_guard.py`)
* Security Secret Scanner (`scripts/secret_scan.py`)
* Full 275-Test Pytest Suite

---

## 21. Running the Live Research Demonstration

### Full-Stack Web App Demo (Recommended for Judges)
**Terminal 1 — API Backend Engine:**
```bash
source .venv311/bin/activate
python -m uvicorn apps.api.app.factory:create_fastapi_app --factory --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend Command Hub:**
```bash
cd apps/web
npm run dev -- -p 3000
```
Open [`http://localhost:3000/buyer`](http://localhost:3000/buyer) to test live OpenFoodFacts shopping queries.

### CLI Research Pilot Script
```bash
PYTHONPATH=. python3 scripts/run_live_cart_research_pilot.py
```

---

## 22. Production Reality Certification & MCP Verification

### Reality Certification
```bash
PYTHONPATH=. python3 scripts/run_production_reality_certification.py
```

### MCP Interoperability Suite
```bash
PYTHONPATH=. python3 scripts/mcp_client_test_runner.py
```

---

## 23. Verification Status Summary

```text
============================== TEST SUITE RESULTS ==============================
Total Tests Executed : 275
Passed               : 275
Failed               : 0
Errors               : 0
Skipped              : 0
Pass Rate            : 100.0%
================================================================================
Master Quality Gate  : PASS
Secret Scanner       : 869 files scanned — 0 secrets leaked
Architecture Guard   : 504 files checked — 0 layer violations
Working Tree         : CLEAN
```

---

## 24. Honest Limitations Statement

To maintain complete transparency for hackathon evaluation:
1. **No Live PSP Money Settlement:** No live production payment keys (Razorpay/Stripe) are loaded. Payment execution is safely demonstrated via `cafeacme.local` sandbox.
2. **OpenFoodFacts Catalog Scope:** Product discovery uses OpenFoodFacts public catalog data.
3. **Merchant Pricing Limitations:** Catalog prices may differ from real-time dynamic checkout pricing.
4. **Shipping & Tax Fees:** Explicitly marked `UNKNOWN` when not returned by catalog APIs.

---

## 25. Design Philosophy (5 Core Principles)

1. **Verify before acting:** Do not convert uncertain data into confident actions.
2. **Separate intelligence from authority:** An AI agent can recommend an action without receiving payment permissions.
3. **Human confirmation for high-risk effects:** Financial effects require explicit cryptographic authorization.
4. **Idempotency everywhere it matters:** Retries must never create duplicate payment effects.
5. **Tell the truth about uncertainty:** Unknown data is represented as unknown. Never guessed. Never silently zeroed.

---

## 26. Release Information

* **System:** RAZERPAY — Mandate Gateway
* **Version:** `v1.5.0`
* **Commit SHA:** `836de91`
* **Buildathon Track:** Autonomous AI Commerce & Agent Payment Protocols (Razorpay Raze Buildathon 2026)
* **Author:** SanthaKumar K ([@SanthaKumar-K-2004](https://github.com/SanthaKumar-K-2004))
* **Primary Language:** Python 3.11 / TypeScript (Next.js 14)

---

## 27. Future Roadmap

```text
Production PSP Integration (Razorpay / Stripe Live Credentials)
        ↓
Merchant OAuth & Credential Management
        ↓
Real-Time Dynamic Merchant Inventory & Pricing APIs
        ↓
Automated Tax & Carrier Shipping Calculation
        ↓
Multi-Tenant Production Infrastructure
```

---

## 28. Author & License

**Developed by:** SanthaKumar K ([@SanthaKumar-K-2004](https://github.com/SanthaKumar-K-2004))
**Buildathon:** Razorpay Raze Buildathon 2026
**Track:** Autonomous AI Commerce & Agent Payment Protocols
**License:** [MIT License](LICENSE)

---

## RAZERPAY

**Research intelligently. Verify explicitly. Authorize deliberately. Execute safely.**

> **NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE.**
