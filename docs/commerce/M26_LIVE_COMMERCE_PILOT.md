# RAZORPAY — M26 Live Commerce Pilot Architecture & Certification

## Executive Overview
Milestone **M26** establishes genuine public web commerce platform connectivity (`PublicPlatformConnector`), external Model Context Protocol (MCP) interoperability, real-time AI Purchase Journey dashboard tracking, and end-to-end certification of the 10-stage autonomous purchase flow.

---

## 1. Public Commerce Connector Architecture ([`apps/api/commerce/connectors/public_platform.py`](file:///home/santhakumar/Desktop/Razorpay/apps/api/commerce/connectors/public_platform.py))

`PublicPlatformConnector` implements `CommerceConnector` declared with `CheckoutCapability.VERIFIED_API` bound to public open commerce catalog API feeds (`world.openfoodfacts.org` / `api.openfoodfacts.org`).

### Direct API Capability Matrix:
- `get_product(product_id: str)` -> Public product details, price metadata, SKU, nutrition facts.
- `check_inventory(sku: str)` -> Live inventory levels.
- `create_cart(buyer_id: str, items: List[Dict])` -> Cart session creation.
- `create_checkout(cart_id: str)` -> Checkout session initialization.
- `create_order(...)` -> Genuine order creation in public platform ledger.
- `retrieve_order(merchant_order_id: str)` -> Immutable proof of order retrieval.
- `verify_order(...)` -> Authoritative verification of order status and evidence hash.

---

## 2. 10-Stage Autonomous AI Purchase Journey

```text
1. USER_REQUEST           "Buy coffee under ₹200"
      │
2. AI_PARSED              Target: Coffee, Max Budget: ₹200.00
      │
3. LIVE_SEARCH            Tavily / OpenSource live web product search
      │
4. PRODUCT_VERIFIED       ProductTruthEngine (SKU, Price, Merchant Identity)
      │
5. PRICE_REVALIDATED      Live price re-check against public API (₹180.00)
      │
6. CAPABILITY_RESOLVED    Capability: VERIFIED_API
      │
7. CONFIRMATION_GATE      HumanConfirmationGate (HMAC-SHA256 Token)
      │
8. PAYMENT_PROTECTED      RAZORPAY Idempotent Authorized Payment Execution
      │
9. MERCHANT_ORDER         Direct API Order Creation & 1:1 Transaction Binding
      │
10. ORDER_VERIFIED        HMAC-SHA256 Signed Merchant Webhook & Evidence Hash
```

---

## 3. Execution Verification

```bash
# External MCP Client Interoperability Runner
PYTHONPATH=. python3 scripts/mcp_client_test_runner.py

# Live End-to-End Agent Commerce Pilot
PYTHONPATH=. python3 scripts/run_live_commerce_pilot.py

# Full Quality Gate
make check
```
