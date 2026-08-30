# RAZERPAY — Checkout Capability Model (M24)

## Capability Classification Matrix

| Capability State | Description | Payment Path | Technical Honesty Rule |
| :--- | :--- | :--- | :--- |
| `VERIFIED_API` | Direct merchant API integration established and authorized. | Direct RAZERPAY API Payment | RAZERPAY handles full API checkout. |
| `CHECKOUT_HANDOFF` | Unintegrated public web store. Product verified, direct API unavailable. | Signed Redirect Handoff Package | RAZERPAY generates signed redirect handoff package for merchant site. |
| `DISCOVERY_ONLY` | Product found in search discovery, but detail/checkout URL unavailable. | Blocked | Browsing only. Purchase execution prohibited. |
| `UNSUPPORTED` | Merchant domain untrusted or invalid. | Blocked | Blocked. |

## Price & Stock Mutation Rules
- Prior to checkout preparation or payment execution, `LivePriceRevalidator` and `LiveAvailabilityRevalidator` recheck live price and stock.
- If price changes (e.g. ₹180 -> ₹240), any existing confirmation token is **invalidated**, and the state transitions to `PRICE_CHANGED`. A new human confirmation is required.
