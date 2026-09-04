# Mandate Gateway — Final Capability Matrix

## System: Mandate Gateway — Verified AI Commerce Agent
## Version: v1.0.0 / v1.0.1 (Audit-Hardened)

> **Disclaimer Notice**: Mandate Gateway is an independent open-source AI commerce safety project. It is **NOT** affiliated with, endorsed by, or connected to **Razorpay Software Private Limited**.

---

## Capability Level Definitions

| Level | Meaning |
|-------|---------|
| **LIVE_CATALOG_API** | Makes real HTTP requests to a public external catalog API (`world.openfoodfacts.org`). Product data is retrieved live. *(Not a merchant checkout API)*. |
| **VERIFIED_API** | Connects to a real or sandbox API; product data is retrieved and provenance-verified. |
| **CHECKOUT_HANDOFF** | Validates HTTPS URLs and generates a checkout handoff URL for browser redirect; does NOT complete API purchases directly. |
| **TEST / SANDBOX** | Uses official test credentials or sandbox API (`https://api.razorpay.com/v1` in test mode / `cafeacme.local`); real money is ❌ NEVER spent. |
| **PROTOCOL_COMPATIBLE** | Provides standard-compatible HTTP 402 / UAP authorization parsing & adapter logic without claiming third-party certification. |
| **DISCOVERY_ONLY** | Can search and evaluate product catalog data; cannot initiate checkout execution. |
| **UNKNOWN** | Data could not be verified; explicitly rendered as `UNKNOWN` in all agent and API outputs. |
| **BLOCKED** | Feature is explicitly excluded from discovery and blocked from direct execution via autonomous MCP clients. |

---

## Commerce & Payment Connectors Classification

| Connector / Protocol | Target Domain / Base URL | Capability Classification | Environment Mode | Real Money Movement? |
|----------------------|-------------------------|---------------------------|------------------|----------------------|
| `PublicPlatformConnector` | `world.openfoodfacts.org` | `LIVE_CATALOG_API` | **LIVE** | ❌ No — Catalog Data Only |
| `RazorpayClient` (Test) | `https://api.razorpay.com/v1` | `TEST / SANDBOX` | **TEST** | ❌ No — Razorpay Test Mode |
| `RazorpayClient` (Live) | `https://api.razorpay.com/v1` | `NOT AVAILABLE` | **LIVE** | 🔴 Disabled — Requires Live Keys |
| `X402PaymentAdapter` | HTTP `402 Payment Required` | `PROTOCOL_COMPATIBLE` | **PROTOCOL_ADAPTER** | ❌ No — Payment Proof Layer |
| `UAPAuthorizationLayer` | Internal Delegated Tokens | `UAP_ALIGNED` | **AUTHORIZATION** | ❌ No — Delegated Policy Engine |
| `RealPlatformConnector` | `cafeacme.local` | `VERIFIED_API` | **SANDBOX** | ❌ No — Local Sandbox API |
| `GenericWebCheckoutConnector` | Validated HTTPS Merchant URLs | `CHECKOUT_HANDOFF` | **LIVE** | ❌ No — Redirect URL Handoff |

---

## Autonomous MCP Tool Exposure & Execution Barrier

| Tool Name | Exposed in `tools/list`? | Executable via `tools/call`? | Permission Level | Notes |
|-----------|--------------------------|------------------------------|------------------|-------|
| `search_products` | ✅ YES | ✅ YES | Public | Live OpenFoodFacts product search |
| `get_product_details` | ✅ YES | ✅ YES | Public | Live product detail fetch |
| `compare_products` | ✅ YES | ✅ YES | Public | Multi-source comparison |
| `recommend_product` | ✅ YES | ✅ YES | Public | Explainable recommendation scoring |
| `research_shopping_request` | ✅ YES | ✅ YES | Public | Multi-item cart research |
| `optimize_cart` | ✅ YES | ✅ YES | Public | Multi-item cart optimizer |
| `get_checkout_capability` | ✅ YES | ✅ YES | Public | Returns capability level per merchant |
| `get_connector_health` | ✅ YES | ✅ YES | Public | Circuit breaker health query |
| `create_purchase_plan` | ✅ YES | ✅ YES | Confirmation-required | Builds plan package; no payment effect |
| `get_budget_status` | ✅ YES | ✅ YES | Public | Budget state query |
| `get_transaction_status` | ✅ YES | ✅ YES | Public | Transaction state query |
| `get_purchase_status` | ✅ YES | ✅ YES | Public | Purchase outcome query |
| `reconcile_commerce_operation` | ✅ YES | ✅ YES | Public | Reconciliation status query |
| `get_payment_capabilities` | ✅ YES | ✅ YES | Public | Payment capability matrix query |
| `get_agent_payment_policy` | ✅ YES | ✅ YES | Public | Agent spending limits & policy query |
| `get_payment_timeline` | ✅ YES | ✅ YES | Public | Real-time transaction event timeline |
| `execute_payment` | 🚫 BLOCKED | 🚫 REJECTED (-32000) | Confirmation-required | Direct execution blocked via MCP |
| `create_merchant_order` | 🚫 BLOCKED | 🚫 REJECTED (-32000) | Restricted | Direct order creation blocked via MCP |
| `execute_confirmed_purchase` | 🚫 BLOCKED | 🚫 REJECTED (-32000) | Confirmation-required | Direct purchase execution blocked via MCP |

---

## Commerce Flow Capabilities

| Flow Step | Capability Level | Real-World Details |
|-----------|-----------------|--------------------|
| Natural language intent parsing | ✅ LIVE | `MultiItemIntentExtractor` parses shopping requests |
| Live product catalog discovery | ✅ LIVE_CATALOG_API | Queries `world.openfoodfacts.org` public API |
| Price truth verification | ✅ LIVE_CATALOG_API | Provenance verified against source catalog |
| Multi-merchant comparison | ✅ LIVE | Across registered catalog & sandbox connectors |
| Multi-item cart optimization | ✅ LIVE (Algorithmic) | Deterministic branch-and-bound optimization |
| Explainable recommendation | ✅ LIVE (Algorithmic) | Multi-factor scored with human-readable notes |
| Delivery / tax fee display | ⚠️ UNKNOWN | Explicitly rendered as `UNKNOWN` if unverifiable |
| Human confirmation gate | ✅ LIVE | HMAC-SHA256 single-use token barrier |
| Razorpay Test Mode order creation | 🟡 TEST / SANDBOX | Official Razorpay v1 REST API (`https://api.razorpay.com/v1`) |
| Razorpay Webhook Verification | ✅ LIVE | HMAC-SHA256 signature & timestamp validation |
| x402 HTTP Payment Parsing | 🔵 PROTOCOL_COMPATIBLE | HTTP 402 requirement parsing & proof generation |
| UAP Delegated Authorization | 🟢 LIVE | Token validation, limits, instant revocation |
| Agent Policy Enforcement | 🟢 ENFORCED | Spending caps, product check, risk classification |
| Payment execution | 🔒 TEST / SANDBOX ONLY | Requires human confirmation + Razorpay Test / Sandbox |
| Real-money production settlement | ❌ NOT AVAILABLE | Never claimed without explicit production keys |
| Checkout handoff (public web merchants) | ✅ LIVE (Handoff) | Validates HTTPS URLs & redirects user |
| Webhook verification | ✅ LIVE | HMAC-SHA256 signature + timestamp expiry |
| Transaction reconciliation | ✅ LIVE | Full idempotent reconciliation engine |

---

## Honest Limitations Summary

1. **OpenFoodFacts Scope**: Product catalog data is retrieved from OpenFoodFacts (food and grocery products). OpenFoodFacts is a product database, not a merchant checkout engine.
2. **Delivery & Tax Fees**: Shipping and tax fees are rendered as `UNKNOWN` because public catalog APIs do not supply real-time shipping quotes.
3. **Razorpay Test Mode Default**: `RAZORPAY_MODE=test` is active by default; real money is never moved without explicit production configuration.
4. **Protocol Compatibility**: x402 and UAP layers are standard-aligned architectural adapters running within Mandate Gateway's safety boundary.
