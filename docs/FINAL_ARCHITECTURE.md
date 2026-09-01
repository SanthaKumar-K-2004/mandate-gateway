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
│   RazerpayMCPServer                 │    │   MultiItemIntentExtractor      │
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
│   • State machine: PENDING → AUTHORIZED → CAPTURED / FAILED               │
│   • ROLLED_BACK on pre-capture failure                                    │
│   • Fail-closed state transitions                                         │
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

## Defense-in-Depth Payment Safety Invariant

> **NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE.**

Enforced across **five defense-in-depth layers**:
1. **Human Confirmation Barrier**: HMAC-SHA256 single-use confirmation token.
2. **Execution Layer Nonces**: DB-persisted cryptographic nonces.
3. **Request Fingerprinting**: Request payload hash matching and replay rejection.
4. **Transaction ↔ Order Binding**: 1:1 binding with duplicate rejection.
5. **Idempotent Reconciliation**: Ledger state audit with SHA-256 evidence hashing.
