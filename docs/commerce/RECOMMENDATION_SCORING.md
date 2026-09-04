# RAZORPAY — Deterministic Recommendation Engine Scoring Model

## Overview
The `DeterministicRecommendationEngine` ([`apps/api/commerce/recommendation_engine.py`](file:///home/santhakumar/Desktop/Razorpay/apps/api/commerce/recommendation_engine.py)) computes composite recommendation scores deterministically.

---

## Scoring Weight Formula

$$\text{Recommendation Score} = S_{\text{Truth}} + S_{\text{Budget}} + S_{\text{Availability}} + S_{\text{Merchant}} + S_{\text{Capability}} + S_{\text{Freshness}} + S_{\text{Health}}$$

| Dimension | Max Points | Criteria |
|---|---|---|
| Product Truth | 25 | `PRODUCT_VERIFIED` (25 pts), `PRICE_UNVERIFIED` (10 pts) |
| Budget Fit | 20 | Within budget (15-20 pts proportional to savings) |
| Availability | 15 | `AVAILABLE` (15 pts), else 0 pts |
| Merchant Confidence | 15 | Verified Domain (15 pts), Unresolved Domain (10 pts) |
| Checkout Capability | 15 | `VERIFIED_API` (15 pts), `CHECKOUT_HANDOFF` (10 pts), `DISCOVERY_ONLY` (5 pts) |
| Source Freshness | 5 | Live retrieval timestamp (5 pts) |
| Connector Health | 5 | Healthy circuit status (5 pts) |
