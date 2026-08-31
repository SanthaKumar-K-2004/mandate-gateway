# RAZERPAY — M28 Autonomous Multi-Item Cart Research Architecture

## Overview
Milestone **M28** upgrades the RAZERPAY AI Commerce Agent into an autonomous multi-item research and dynamic cart intelligence system.

---

## 1. Multi-Item Research Architecture

```text
User Request ("Find coffee and biscuits under ₹300")
       │
MultiItemIntentExtractor
       │
       ├── ShoppingItemIntent("Coffee", quantity=1)
       └── ShoppingItemIntent("Biscuits", quantity=1)
       │
CartResearchEngine (Parallel Bounded Research)
       │
       ├── Item 1 Candidates (OpenFoodFacts API)
       └── Item 2 Candidates (Cafe Acme API)
       │
CartOptimizer (Branch-and-Bound Combination Search)
       │
CartCostEngine (Verified Product Subtotal vs UNKNOWN Fees)
       │
DeterministicRecommendationEngine (Explainable Cart Scoring)
```

---

## 2. Total Cost Truth Policy

- If shipping cost, merchant tax, or platform fees cannot be verified from live evidence, they are explicitly marked as **`UNKNOWN`**.
- Incomplete totals are never displayed as final payable amounts.
