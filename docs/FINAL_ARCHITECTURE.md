# Mandate Gateway — Final Architecture Specification

## System: Mandate Gateway — Verified AI Commerce Agent
## Version: v1.0.0 / v1.0.1 (Audit-Hardened)

> **Disclaimer Notice**: Mandate Gateway is an independent open-source AI commerce safety project. It is **NOT** affiliated with, endorsed by, or connected to **Razorpay Software Private Limited**.

---

## End-to-End System Request & Security Flow

```text
User Input (Natural Language)
        │
        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                           User Interface Layer                            │
│   Control Center UI  ·  REST API  ·  MCP Client Interface                  │
│   POST /api/v1/commerce/shopping/research                                 │
│   POST /api/v1/commerce/shopping/optimize                                 │
│   POST /api/v1/agent/run                                                  │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                            AI Agent Runtime                               │
│   AgentRuntime  ·  ToolProxy  ·  AIToolRegistry                           │
│   • Bounded iteration guard (max steps enforced)                          │
│   • Infinite loop detection & cancellation handling                       │
│   • Secret-redacted structured JSON logging                               │
└──────────────────────┬────────────────────────────────┬───────────────────┘
                       │                                │
                       ▼                                ▼
┌─────────────────────────────────────┐    ┌────────────────────────────────┐
│      MCP Protocol Server Layer      │    │   Multi-Item Intent Extractor   │
│   RazorpayMCPServer                 │    │   MultiItemIntentExtractor      │
│   JSON-RPC 2.0 Interface            │    │   ShoppingRequest Model        │
│   • 13 discovery tools exposed      │    │   CartOptimizationStrategy     │
│   • 3 execution tools BLOCKED       │    └───────────────┬────────────────┘
│     (tools/list & tools/call)       │                    │
└──────────────────────┬──────────────┘                    ▼
                       │                   ┌────────────────────────────────┐
                       │                   │   Parallel Cart Research       │
                       │                   │   CartResearchEngine           │
                       │                   │   (bounded concurrency)        │
                       │                   └───────────────┬────────────────┘
                       │                                   │
                       ▼                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                       Live Data Providers & Connectors                    │
│                                                                           │
│   PublicPlatformConnector            RealPlatformConnector                │
│   world.openfoodfacts.org            cafeacme.local (SANDBOX)             │
│   Capability: LIVE_CATALOG_API       Capability: VERIFIED_API             │
│   Mode: LIVE                         Mode: SANDBOX                        │
│                                                                           │
│   GenericWebCheckoutConnector                                             │
│   Capability: CHECKOUT_HANDOFF                                            │
│   Mode: LIVE (Validated HTTPS URLs only — Handoff Redirect)               │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         Product Truth Engine                              │
│   ProductTruthEngine.evaluate_product()                                   │
│   • Queries live provider API                                             │
│   • Verifies SKU, price, and availability against source catalog          │
│   • Assigns status: PRODUCT_VERIFIED / SOURCE_BACKED / UNVERIFIED        │
│   • Fail-closed: unverified products block checkout execution             │
│   • SHA-256 evidence hash generated per verified item                     │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
               ┌──────────────────────┼──────────────────────┐
               ▼                      ▼                      ▼
┌──────────────────────────┐ ┌──────────────────┐ ┌─────────────────────────┐
│ Multi-Source Discovery   │ │ Cart Cost Engine │ │ Recommendation Engine   │
│ Engine                   │ │ CartCostEngine   │ │ RecommendationEngine    │
│ Deduplication & ranking  │ │ Verified costs   │ │ Explainable multi-factor│
│ Product evidence model   │ │ Shipping/tax:    │ │ scored notes            │
│                          │ │ UNKNOWN          │ │                         │
└──────────────────────────┘ └──────────────────┘ └─────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                          Cart Combination Optimizer                       │
│   CartOptimizer (Branch-and-Bound Algorithm)                              │
│   • Strategies: LOWEST_TOTAL_PRICE, BEST_VALUE, FEWEST_MERCHANTS, etc.     │
│   • Budget bound enforcement                                              │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    Checkout Preparation & Human Gate                      │
│   CheckoutOrchestrator.prepare_checkout_flow()                            │
│   • Live price re-validation & staleness check                            │
│   • Plan hash binding (cryptographic)                                     │
│                                                                           │
│   HumanConfirmationGate                                                   │
│   • HMAC-SHA256 single-use confirmation tokens                            │
│   • Cryptographic binding: token → request_id + merchant + buyer + amount │
│   • Single-use: consumed on first verify attempt; replay REJECTED          │
│   • Expiration TTL enforced                                               │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    Agentic Payment Protocol & Policy Engine               │
│   AgentPaymentProtocol  ·  AgentPaymentPolicyEngine                      │
│   • Deterministic policy: spending limits, product verification gate      │
│   • Zero LLM involvement in payment execution decisions                   │
│   • Risk Classifier: LOW / MEDIUM / HIGH / BLOCKED                        │
│                                                                           │
│   ┌─────────────────────┬─────────────────────┬──────────────────────┐    │
│   │  Razorpay Connector │   x402 Payment      │   UAP Authorization  │    │
│   │  (Test Mode / v1)   │   Adapter (HTTP 402)│   Layer (Delegated)  │    │
│   │  • https://api.     │   • Parse 402 headers│  • Delegation tokens │    │
│   │    razorpay.com/v1  │   • Proof generation│  • Spending limits   │    │
│   │  • Minor units paise│   • Replay protection│ • Revocation status │    │
│   │  • Webhook HMAC     │   • Hash binding    │  • Scope checks      │    │
│   └─────────────────────┴─────────────────────┴──────────────────────┘    │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         Payment Safety Layer                              │
│   AuthorizationEngine  ·  BudgetReservationEngine                         │
│   NonceEngine  ·  StepUpChallengeEngine  ·  ReplayProtection              │
│   • Single-use DB-persisted nonces                                        │
│   • Request fingerprint replay rejection                                  │
│   • Budget reservation before payment authorization                       │
│   • Step-up challenge for high-value transactions                         │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                        Order Binding & Execution                          │
│   CommerceTransactionBindingManager                                       │
│   • Cryptographic 1:1 binding: payment_tx_id ↔ merchant_order_id          │
│   • Duplicate binding REJECTED (TransactionBindingError)                  │
│   • Ed25519 signed action receipts (immutable audit trail)                │
│                                                                           │
│   ExecutionEngine                                                         │
│   • State machine: CREATED → AUTHORIZED → CAPTURED / FAILED / REFUNDED    │
│   • ROLLED_BACK on pre-capture failure                                    │
│   • Fail-closed state transitions (UNKNOWN maps to manual review)        │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         Webhook Security Layer                            │
│   CommerceWebhookHandler                                                  │
│   • HMAC-SHA256 signature verification                                    │
│   • Timestamp expiration window enforcement                               │
│   • Replay attack detection & incident trigger                            │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         Reconciliation Engine                             │
│   CommerceReconciliationEngine                                            │
│   States: BOTH_CONFIRMED / PAYMENT_ONLY / ORDER_ONLY / UNRESOLVED         │
│   • PAYMENT_ONLY → manual review required                                 │
│   • Idempotent record lookup & SHA-256 evidence hashing                   │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    Monitoring & Operations Layer                          │
│   Prometheus Exporter (/metrics)   Grafana Production Dashboards (5)      │
│   Structured Logger (Redacted)     Incident Engine                        │
│   /health + /ready Probes          Audit Ledger (SHA-256 Hash Chain)       │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Agentic Payment Protocol Layer & Subsystems

### 1. Razorpay Test-Mode Connector (`apps/api/commerce/payments/razorpay_client.py`)
- Official v1 REST API integration (`https://api.razorpay.com/v1`).
- Operates strictly in minor integer units (paise: ₹299 = 29900 paise) to prevent floating-point calculation errors.
- Enforces HMAC-SHA256 signature verification for payment payloads and webhooks (`X-Razorpay-Signature`).
- Secret Redaction: `RAZORPAY_KEY_SECRET` and `RAZORPAY_WEBHOOK_SECRET` wrapped in `SecretString` to prevent leakage in logs, exceptions, or responses.

### 2. x402 HTTP Payment Adapter (`apps/api/commerce/payments/x402.py`)
- Protocol-compatible adapter for HTTP `402 Payment Required` negotiation workflows.
- Parses 402 requirement headers, binds payment specifications (resource, recipient, amount, currency, network), generates proof payloads, and validates signatures.
- Includes proof replay prevention cache to prevent double-spending of proof tokens.

### 3. UAP-Aligned Authorization Layer (`apps/api/commerce/payments/uap.py`)
- Delegated authority framework for AI agents.
- Supports authorization lifecycle: `ACTIVE`, `REVOKED`, `EXPIRED`, `CONSUMED`, `SUSPENDED`.
- Enforces per-transaction limits, daily cumulative limits, category velocity, and merchant scope boundaries.
- Immediate fail-closed behavior on revoked or expired authorization tokens.

### 4. Agent Payment Policy Engine (`apps/api/commerce/payments/policy.py`)
- Deterministic evaluation engine for payment requests.
- Evaluates agent identity, request payload, spending limits, product evidence verification status, and human confirmation tokens.
- Deterministic Risk Classifier: `LOW`, `MEDIUM`, `HIGH`, `BLOCKED`. Zero LLM involvement in payment authority decisions.

---

## Defense-in-Depth Payment Safety Invariant

> **NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE.**

Enforced across **five defense-in-depth layers**:
1. **Human Confirmation Barrier**: HMAC-SHA256 single-use confirmation token.
2. **Execution Layer Nonces**: DB-persisted cryptographic nonces.
3. **Request Fingerprinting**: Request payload hash matching and replay rejection.
4. **Transaction ↔ Order Binding**: 1:1 binding with duplicate rejection.
5. **Idempotent Reconciliation**: Ledger state audit with SHA-256 evidence hashing.
