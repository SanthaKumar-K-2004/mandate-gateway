# RAZERPAY — Final Capability Matrix

## System: Mandate Gateway — AI Commerce Agent
## Version: v1.0.0 | Commit: efe7f94 (see Release Readiness for full hash)

---

> **Honesty Principle**: Every capability below is exactly what the system can and cannot do in its current state. Nothing is exaggerated.

---

## Capability Level Definitions

| Level | Meaning |
|-------|---------|
| **LIVE** | Makes real HTTP requests to a public external API. Data returned is real. |
| **VERIFIED_API** | Connects to a real API; product data is retrieved and provenance-verified. |
| **CHECKOUT_HANDOFF** | Generates a checkout URL for a web merchant; does NOT complete the purchase directly. |
| **SANDBOX** | Uses a controlled test environment (cafeacme.local); not a real production merchant. |
| **DISCOVERY_ONLY** | Can find and evaluate product data; cannot initiate any checkout flow. |
| **UNKNOWN** | Data could not be verified; explicitly labelled as UNKNOWN in all outputs. |
| **BLOCKED** | Feature exists in registry but is explicitly excluded from autonomous MCP exposure. |

---

## Commerce Connectors

| Connector | Target Domain | Mode | Checkout Capability | Real Money? |
|-----------|--------------|------|---------------------|-------------|
| `PublicPlatformConnector` | `world.openfoodfacts.org` | LIVE | VERIFIED_API (discovery + price truth) | ❌ No — data only |
| `RealPlatformConnector` | `cafeacme.local` | SANDBOX | VERIFIED_API (API-connected sandbox) | ❌ No — sandbox |
| `GenericWebCheckoutConnector` | Any web merchant | LIVE | CHECKOUT_HANDOFF | ❌ No — handoff URL only |

---

## MCP Tool Exposure

| Tool | Exposed via MCP? | Permission Level | Notes |
|------|-----------------|------------------|-------|
| `search_products` | ✅ YES | Public | Live OpenFoodFacts discovery |
| `get_product_details` | ✅ YES | Public | Live product detail fetch |
| `compare_products` | ✅ YES | Public | Multi-source comparison |
| `recommend_product` | ✅ YES | Public | Explainable scoring |
| `research_shopping_request` | ✅ YES | Public | Multi-item cart research |
| `optimize_cart` | ✅ YES | Public | Cart combination optimizer |
| `get_checkout_capability` | ✅ YES | Public | Returns capability level per merchant |
| `get_connector_health` | ✅ YES | Public | Circuit breaker health status |
| `create_purchase_plan` | ✅ YES | Confirmation-required | Builds plan, does NOT execute |
| `get_budget_status` | ✅ YES | Public | Budget state query |
| `get_transaction_status` | ✅ YES | Public | Transaction state query |
| `get_purchase_status` | ✅ YES | Public | Purchase outcome query |
| `reconcile_commerce_operation` | ✅ YES | Public | Reconciliation query |
| `execute_payment` | 🚫 BLOCKED | Confirmation-required | Never exposed to autonomous MCP |
| `create_merchant_order` | 🚫 BLOCKED | Restricted | Never exposed to autonomous MCP |

---

## Product Truth / Verification Status

| Status | Meaning | Action Allowed |
|--------|---------|----------------|
| `PRODUCT_VERIFIED` | SKU, price, availability all confirmed from live source | Checkout preparation allowed |
| `SOURCE_BACKED` | Source URL valid, some data confirmed, full verification incomplete | Checkout preparation allowed with caveats |
| `UNVERIFIED` | Could not confirm product data from source | Checkout BLOCKED (fail-closed) |

---

## Commerce Flow Capabilities

| Flow Step | Capability | Notes |
|-----------|-----------|-------|
| Natural language intent parsing | ✅ LIVE | MultiItemIntentExtractor |
| Live product search | ✅ LIVE | OpenFoodFacts public API |
| Price truth verification | ✅ LIVE | Against live source |
| Multi-merchant comparison | ✅ LIVE | Across registered connectors |
| Cart optimization (multi-item) | ✅ LIVE (algorithmic) | Branch-and-bound, deterministic |
| Recommendation (explainable) | ✅ LIVE (algorithmic) | Multi-factor scored |
| Delivery/tax fee display | ⚠️ UNKNOWN | Explicitly shown as UNKNOWN if unverifiable |
| Human confirmation gate | ✅ LIVE | HMAC-SHA256 single-use token |
| Direct payment execution | 🔒 SANDBOX ONLY | Requires human confirmation + cafeacme.local |
| Direct order creation at real merchant | ❌ NOT SUPPORTED | No real merchant API credentials configured |
| Checkout handoff (any web merchant) | ✅ LIVE | URL generation + redirect |
| Webhook verification | ✅ LIVE | HMAC-SHA256 + timestamp |
| Reconciliation | ✅ LIVE | Full idempotent reconciliation engine |

---

## Security Capabilities

| Feature | Status | Implementation |
|---------|--------|----------------|
| Single-use payment confirmation | ✅ ENFORCED | HMAC-SHA256 tokens, DB-consumed |
| Duplicate payment prevention | ✅ ENFORCED | 5 independent mechanisms |
| Replay attack prevention | ✅ ENFORCED | Nonce + fingerprint + token single-use |
| Webhook forgery detection | ✅ ENFORCED | HMAC-SHA256, replay + timestamp |
| Secret redaction in logs | ✅ ENFORCED | Automated key-pattern redaction |
| Autonomous payment tool blocking | ✅ ENFORCED | MCP exclusion list |
| Fail-closed on unverified products | ✅ ENFORCED | UNVERIFIED → checkout blocked |
| Cryptographic audit trail | ✅ ENFORCED | Ed25519 + SHA-256 hash chain |
| Budget enforcement | ✅ ENFORCED | Pre-authorization budget reservation |

---

## Known Limitations (Honest)

| Limitation | Detail |
|-----------|--------|
| **No real merchant credentials** | `cafeacme.local` is a sandbox merchant. Real checkout with real money is NOT supported. |
| **OpenFoodFacts = food products only** | Discovery is limited to food/grocery categories from OpenFoodFacts. |
| **Delivery/tax fees UNKNOWN** | Shipping and tax cannot be verified from available APIs; always shown as UNKNOWN. |
| **No persistent storage in default mode** | SQLite in-process (dev); PostgreSQL required for production persistence across restarts. |
| **No real payment gateway integration** | No Razorpay, Stripe, or other PSP API credentials are wired. |
| **MCP client is unauthenticated in dev** | Production MCP requires auth; dev mode has no tenant isolation. |
| **OpenFoodFacts rate limits** | Heavy concurrent usage may be throttled by the free public API. |
| **cafeacme.local requires local DNS** | Sandbox merchant domain requires hosts file entry or local DNS. |

---

## What Is Genuinely Live vs Not

### ✅ Genuinely Live (Real HTTP, Real Data)
- Product discovery via `world.openfoodfacts.org` public API
- Product provenance verification against OpenFoodFacts
- All algorithmic layers (cart research, optimization, recommendation)
- All safety/security enforcement mechanisms
- All reconciliation and audit trail mechanics
- Prometheus metrics export (`/metrics` endpoint)
- Health/readiness endpoints

### ⚠️ Sandbox / Controlled (Not Real Money)
- Payment execution (`cafeacme.local` sandbox merchant)
- Direct merchant order creation (sandbox only)
- Mandate/authorization domain (mandate gateway — not commerce PSP)

### ❌ Not Available in Current Build
- Real PSP (Razorpay/Stripe) payment processing
- Real merchant credentials for any production commerce site
- Real delivery fee/tax APIs
- OAuth/credential management for external merchant APIs
