# RAZERPAY — M27 Multi-Merchant Connector Network & Comparison Architecture

## Overview
Milestone **M27** expands RAZERPAY into a resilient multi-merchant commerce network.

---

## 1. Multi-Merchant Network Topology

```text
RAZERPAY Commerce Network
│
├── Connector Registry (CommerceConnectorRegistry)
│
├── Product Discovery Connectors
│   ├── Public Platform Connector (OpenFoodFacts API)
│   ├── Merchant Search Connector (Cafe Acme Direct API)
│   └── Web Discovery Connector (Generic Web Stores)
│
├── Canonical Product Normalizer (CanonicalProduct)
├── Product Deduplication Engine (ProductDeduplicator)
├── Cross-Merchant Comparison Engine (ProductComparisonEngine)
├── Deterministic Recommendation Engine (DeterministicRecommendationEngine)
└── RAZERPAY Payment & Checkout Pipeline
```

---

## 2. Capability Matrix

| Connector | Domain | Capability | Environment | Description |
|---|---|---|---|---|
| `PublicPlatformConnector` | `world.openfoodfacts.org` | `VERIFIED_API` | `LIVE` | Direct public catalog API integration |
| `RealPlatformConnector` | `cafeacme.local` | `VERIFIED_API` | `SANDBOX` | Demonstration merchant API adapter |
| `GenericWebCheckoutConnector` | `public_web_stores` | `CHECKOUT_HANDOFF` | `LIVE` | Signed redirect handoff |
