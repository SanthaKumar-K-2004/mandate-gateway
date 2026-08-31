# RAZERPAY — Real Merchant Platform Connector (M25)

## Overview
The `RealPlatformConnector` ([`apps/api/commerce/connectors/real_platform.py`](file:///home/santhakumar/Desktop/Razorpay/apps/api/commerce/connectors/real_platform.py)) provides direct API integration with authenticated merchant commerce engines (e.g. `cafeacme.local`).

Unlike web checkout redirect handoffs, `RealPlatformConnector` is declared with explicit capability `VERIFIED_API` and genuinely executes direct merchant API calls.

## Supported Operations
1. `get_product(product_id)`: Fetches product metadata directly from merchant catalog API.
2. `check_inventory(sku)`: Verifies real-time stock levels.
3. `create_cart(buyer_id, items)`: Creates a merchant cart session.
4. `create_checkout(cart_id)`: Initializes a merchant checkout session.
5. `create_order(request_id, buyer_id, product, payment_transaction_id, order_binding_hash)`: Executes genuine merchant order creation upon payment authorization.
6. `retrieve_order(merchant_order_id)`: Fetches merchant order proof.
7. `verify_order(order_id, payment_transaction_id)`: Authoritatively verifies order outcome.
