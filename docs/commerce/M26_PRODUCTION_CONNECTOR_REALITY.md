# RAZERPAY — M26 Production Commerce Reality Matrix & Hardening

## Overview
Milestone **M26** enforces strict truth-in-labeling across all commerce connectors, network clients, reconciliation engines, and dashboard UIs.

---

## 1. Honest Environment & Capability Classification

Every commerce connector in RAZERPAY explicitly declares both its **Checkout Capability** and **Environment Mode**:

| Connector | Domain | Capability | Environment | Description |
|---|---|---|---|---|
| `PublicPlatformConnector` | `world.openfoodfacts.org` | `VERIFIED_API` | `LIVE` | Direct public catalog API integration for product facts & order evidence |
| `RealPlatformConnector` | `cafeacme.local` | `VERIFIED_API` | `SANDBOX` | Demonstration merchant API adapter for local/sandbox testing |
| `GenericWebCheckoutConnector` | `public_web_stores` | `CHECKOUT_HANDOFF` | `LIVE` | Secure signed redirect handoff to official merchant checkout sites |

> [!IMPORTANT]
> **Production Fail-Closed Guard**: When `APP_ENV=production`, `CommerceConnectorConfigManager` strictly rejects any connector configured as `DEMO` or using non-HTTPS base URLs.

---

## 2. Core Safety Invariants

1. **Zero Double Execution**: No payment or order creation request is ever retried automatically if transaction state is uncertain.
2. **Payment ↔ Order Reconciliation**: If payment succeeds but merchant order creation status is uncertain, the system sets state `PAYMENT_SUCCESS_ORDER_UNKNOWN` and queues automated reconciliation.
3. **Credential Security**: Secret keys, partner API tokens, and webhook secrets are redacted in all logs, API responses, and dashboard views.
