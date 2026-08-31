# RAZERPAY — Bounded Cart Combination Optimizer

## Overview
The `CartOptimizer` ([`apps/api/commerce/cart_optimizer.py`](file:///home/santhakumar/Desktop/Razorpay/apps/api/commerce/cart_optimizer.py)) evaluates multi-item cart combinations.

---

## Optimization Strategies

1. **`BEST_VALUE`**: Balances budget efficiency, product truth verification, merchant count, and checkout capability.
2. **`LOWEST_TOTAL_PRICE`**: Prioritizes minimum total known product cost.
3. **`FEWEST_MERCHANTS`**: Rewards single-merchant combinations to minimize shipping fragmentation.
4. **`HIGHEST_TRUST`**: Prioritizes verified identity and direct API capability.
5. **`BALANCED`**: Equal weighting across all dimensions.
