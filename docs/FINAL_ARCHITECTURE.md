# RAZERPAY — Final Architecture

## System: Mandate Gateway — Production-Grade AI Commerce Agent

---

## End-to-End Request Flow

```
User Input (Natural Language)
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│                     User Interface Layer                          │
│   Control Center UI  ·  REST API  ·  MCP Client Interface         │
│   POST /api/v1/commerce/shopping/research                         │
│   POST /api/v1/commerce/shopping/optimize                         │
│   POST /api/v1/agent/run                                          │
└──────────────────────────────┬────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│                       AI Agent Runtime                            │
│   AgentRuntime  ·  ToolProxy  ·  AIToolRegistry                   │
│   • Bounded iteration (max steps enforced)                        │
│   • Infinite loop detection                                       │
│   • Cancellation signal handling                                  │
│   • Structured JSON logging (every step)                          │
└────────────────┬──────────────────────────────┬───────────────────┘
                 │                              │
                 ▼                              ▼
┌───────────────────────┐          ┌────────────────────────────┐
│   MCP Protocol Layer  │          │  Multi-Item Intent Parser  │
│   RazerpayMCPServer   │          │  MultiItemIntentExtractor  │
│   JSON-RPC 2.0        │          │  ShoppingRequest model     │
│   13 tools exposed    │          │  CartOptimizationStrategy  │
│   (2+ EXCLUDED:       │          └──────────────┬─────────────┘
│   execute_payment,    │                         │
│   create_merchant_    │                         ▼
│   order BLOCKED)      │          ┌────────────────────────────┐
└───────────────────────┘          │  Parallel Cart Research    │
                                   │  CartResearchEngine        │
                 │                 │  (bounded concurrency)     │
                 ▼                 └──────────────┬─────────────┘
┌───────────────────────────────────────────────────────────────────┐
│                  Live Data Provider Layer                         │
│                                                                   │
│   PublicPlatformConnector          RealPlatformConnector          │
│   world.openfoodfacts.org          cafeacme.local (SANDBOX)       │
│   Capability: VERIFIED_API         Capability: VERIFIED_API       │
│   Mode: LIVE                       Mode: SANDBOX                  │
│                                                                   │
│   GenericWebCheckoutConnector                                     │
│   Capability: CHECKOUT_HANDOFF                                    │
│   (any web merchant — handoff only, no direct API)                │
└──────────────────────────────┬────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│                   Product Truth Engine                            │
│   ProductTruthEngine.evaluate_product()                           │
│   • Fetches live data from provider                               │
│   • Verifies SKU, price, availability against source              │
│   • Assigns: PRODUCT_VERIFIED / SOURCE_BACKED / UNVERIFIED        │
│   • Fail-closed: no invented data ever returned as verified       │
│   • Evidence hash (SHA-256) computed per verified product         │
└──────────────────────────────┬────────────────────────────────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│ Multi-Merchant   │  │  Cart Cost Truth │  │  Recommendation      │
│ Discovery Engine │  │  Engine          │  │  Engine              │
│                  │  │  CartCostEngine  │  │  RecommendationEngine│
│ Deduplication    │  │  • Only verified │  │  Explainable scores  │
│ Price comparison │  │    fees included │  │  Multi-factor rank   │
│ Evidence ranking │  │  • Shipping/tax: │  │  Human-readable      │
│                  │  │    UNKNOWN if    │  │  justifications      │
│                  │  │    unverified    │  │                      │
└──────────────────┘  └──────────────────┘  └──────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│                    Cart Optimizer                                 │
│   CartOptimizer (branch-and-bound)                                │
│   • LOWEST_TOTAL_PRICE / BEST_VALUE / FEWEST_MERCHANTS            │
│   • HIGHEST_TRUST / BALANCED strategies                           │
│   • Budget constraint enforcement                                 │
│   • Multi-item combination evaluation                             │
└──────────────────────────────┬────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│              Checkout Preparation & Human Confirmation            │
│   CheckoutOrchestrator.prepare_checkout_flow()                    │
│   • Live price re-validation (staleness guard)                    │
│   • Live availability re-validation                               │
│   • Plan hash binding (cryptographic)                             │
│                                                                   │
│   HumanConfirmationGate                                           │
│   • HMAC-SHA256 signed single-use confirmation tokens             │
│   • Cryptographic binding: token → request_id + merchant + amount │
│   • Single-use: token consumed on first verify, replay REJECTED   │
│   • TTL expiration enforced                                       │
└──────────────────────────────┬────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│                   Payment Safety Layer                            │
│   AuthorizationEngine  ·  BudgetReservationEngine                 │
│   NonceEngine  ·  StepUpChallengeEngine  ·  ReplayProtection      │
│   • Per-request nonce (single-use, DB-persisted)                  │
│   • Replay fingerprint rejection                                  │
│   • Budget enforcement before any payment effect                  │
│   • Step-up challenge for high-value transactions                 │
└──────────────────────────────┬────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│                  Order Binding & Execution                        │
│   CommerceTransactionBindingManager                               │
│   • Cryptographic 1:1 binding: payment_tx_id ↔ merchant_order_id  │
│   • Duplicate binding REJECTED (TransactionBindingError)          │
│   • Ed25519 signed action receipts (immutable audit trail)        │
│                                                                   │
│   ExecutionEngine                                                 │
│   • State machine: PENDING → AUTHORIZED → CAPTURED / FAILED       │
│   • ROLLED_BACK if pre-capture failure                            │
│   • Fail-closed at every state transition                         │
└──────────────────────────────┬────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│                    Webhook Security Layer                         │
│   CommerceWebhookHandler                                          │
│   • HMAC-SHA256 signature verification on every webhook           │
│   • Timestamp expiration window enforcement                       │
│   • Replay attack detection                                       │
│   • WEBHOOK_FORGERY_DETECTED incident raised on repeated failures  │
└──────────────────────────────┬────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│                   Reconciliation Engine                           │
│   CommerceReconciliationEngine                                    │
│   States: BOTH_CONFIRMED / PAYMENT_ONLY / ORDER_ONLY / UNRESOLVED │
│   • PAYMENT_ONLY → manual review required                         │
│   • Idempotent: same tx_id always returns same record             │
│   • Evidence hash (SHA-256) per reconciliation record             │
└──────────────────────────────┬────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────────┐
│              Monitoring & Production Operations                   │
│   Prometheus Metrics    Grafana Dashboards (5)                    │
│   Structured Logging    Incident Engine                           │
│   /metrics endpoint     /health + /ready endpoints                │
│   SLO tracking          Circuit breaker health                    │
│   Secret redaction      Audit ledger (SHA-256 hash-chain)         │
└───────────────────────────────────────────────────────────────────┘
```

---

## Component Registry

| Component | Module | Key Guarantee |
|-----------|--------|---------------|
| AI Agent Runtime | `apps/api/agent/runtime.py` | Bounded iterations, loop detection |
| MCP Server | `apps/api/agent/mcp_server.py` | 13 tools exposed; execute_payment + create_merchant_order BLOCKED |
| Tool Registry | `apps/api/agent/tool_registry.py` | 15 tools registered, permission-classified |
| Confirmation Gate | `apps/api/agent/confirmation_gate.py` | HMAC-SHA256, single-use, TTL |
| Product Truth Engine | `apps/api/commerce/product_truth_engine.py` | Fail-closed, evidence-hashed |
| Multi-Source Discovery | `apps/api/commerce/multi_source_discovery.py` | Deduplication, source ranking |
| Cart Research | `apps/api/commerce/cart_research.py` | Parallel bounded, stale-filtered |
| Cart Cost Engine | `apps/api/commerce/cart_cost_engine.py` | UNKNOWN for unverified fees |
| Cart Optimizer | `apps/api/commerce/cart_optimizer.py` | Branch-and-bound, deterministic |
| Recommendation Engine | `apps/api/commerce/recommendation_engine.py` | Explainable, multi-factor |
| Checkout Orchestrator | `apps/api/commerce/checkout_orchestrator.py` | Live re-validation, plan hash |
| Transaction Binding | `apps/api/commerce/transaction_binding.py` | 1:1 binding, duplicate rejected |
| Reconciliation Engine | `apps/api/commerce/reconciliation.py` | Idempotent, evidence-hashed |
| Webhook Handler | `apps/api/commerce/webhooks.py` | HMAC-SHA256, replay detection |
| Connector: Public | `apps/api/commerce/connectors/public_platform.py` | LIVE / VERIFIED_API |
| Connector: Real | `apps/api/commerce/connectors/real_platform.py` | SANDBOX / VERIFIED_API |
| Connector: Generic Web | `apps/api/commerce/connectors/generic_web.py` | CHECKOUT_HANDOFF only |
| Prometheus Exporter | `apps/api/observability/prometheus_exporter.py` | HTTP + AI + commerce metrics |
| Incident Engine | `apps/api/observability/incident_engine.py` | Security incident lifecycle |

---

## Data Flow: Single Item Purchase (Happy Path)

```
1. User → "Buy me Ethiopian coffee under ₹300"
2. Agent → MultiItemIntentExtractor → ShoppingRequest
3. Agent → search_products tool → ProductTruthEngine
4. ProductTruthEngine → PublicPlatformConnector → OpenFoodFacts API (LIVE)
5. ProductTruthEngine → verify SKU + price + availability
6. ProductTruthEngine → returns ProductTruth (SOURCE_BACKED or PRODUCT_VERIFIED)
7. Agent → recommend_product → RecommendationEngine (explainable score)
8. Agent → CheckoutOrchestrator.prepare_checkout_flow()
9. CheckoutOrchestrator → live price re-validation + live availability check
10. CheckoutOrchestrator → HumanConfirmationGate.generate_token() [HMAC-SHA256]
11. → STOP: Human reads cart summary + all UNKNOWN fees explicitly shown
12. Human → confirms → token presented
13. HumanConfirmationGate.verify_and_consume_token() → token consumed (single-use)
14. ExecutionEngine → PENDING → AUTHORIZED → CAPTURED
15. CommerceTransactionBindingManager → 1:1 binding created
16. CommerceWebhookHandler → HMAC-verified webhook received
17. CommerceReconciliationEngine → BOTH_CONFIRMED
18. Ed25519 action receipt → immutable audit record
```

## Core Invariant

> **NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE**

Enforced by 5 independent mechanisms:
1. Single-use HMAC confirmation tokens (gate layer)
2. DB-persisted cryptographic nonces (execution layer)
3. Replay fingerprint rejection (request layer)
4. 1:1 transaction ↔ order binding with duplicate rejection (binding layer)
5. Idempotent reconciliation with evidence hashing (reconciliation layer)
