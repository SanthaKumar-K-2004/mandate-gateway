# RAZERPAY — Cross-Merchant Product Comparison Architecture

## Overview
The `ProductComparisonEngine` ([`apps/api/commerce/product_comparison.py`](file:///home/santhakumar/Desktop/Razorpay/apps/api/commerce/product_comparison.py)) performs evidence-backed cross-merchant evaluations.

---

## Comparison Factors

1. **Price & Budget Fit**: Candidate price vs. max budget limit.
2. **Product Truth Verification**: Exact SKU and detail page verification state.
3. **Availability**: Live stock status (`AVAILABLE` vs `OUT_OF_STOCK`).
4. **Merchant Identity**: Identity resolution status.
5. **Checkout Capability**: `VERIFIED_API`, `CHECKOUT_HANDOFF`, or `DISCOVERY_ONLY`.
6. **Source Freshness & Connector Health**: Latency and circuit status.

> [!NOTE]
> Comparisons evaluate objective evidence signals exclusively. Subjective LLM opinions are excluded from factual ranking calculations.
