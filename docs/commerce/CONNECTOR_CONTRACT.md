# RAZORPAY — Commerce Connector Interface Contract

## Overview
Every commerce connector in RAZORPAY implements the abstract contract defined in [`apps/api/commerce/connectors/base.py`](file:///home/santhakumar/Desktop/Razorpay/apps/api/commerce/connectors/base.py).

---

## Required Operations & Standard Fallbacks

```text
discover_products(query, max_price_paise)  -> CommerceConnectorResult
get_product(product_id)                    -> CommerceConnectorResult
revalidate_product(product)                 -> CommerceConnectorResult
prepare_checkout(request_id, product, buyer) -> CommerceConnectorResult
verify_order(order_id, tx_id)              -> CommerceConnectorResult
reconcile(request_id, tx_id)                -> CommerceConnectorResult
```

> [!IMPORTANT]
> If a connector does not support a specific operation, it returns explicit status `"UNSUPPORTED"` rather than simulating false success.
