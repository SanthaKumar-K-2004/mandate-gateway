# RAZORPAY — Total Cost Truth Model

## Overview
The `CartCostEngine` ([`apps/api/commerce/cart_cost_engine.py`](file:///home/santhakumar/Desktop/Razorpay/apps/api/commerce/cart_cost_engine.py)) calculates exact known product costs and enforces strict truth-in-labeling for unverified fees.

---

## Cost Fields

- `product_subtotal_paise`: Sum of verified product price $\times$ quantity.
- `shipping_cost_paise`: `None` if unverified.
- `tax_paise`: `None` if unverified.
- `total_known_cost_paise`: Sum of verified components.
- `unknown_cost_components`: List of unverified fee tags (e.g. `["SHIPPING_COST", "MERCHANT_TAX"]`).

> [!CAUTION]
> If shipping or tax cannot be verified from live evidence, estimation is strictly forbidden. They are rendered as `UNKNOWN`.
