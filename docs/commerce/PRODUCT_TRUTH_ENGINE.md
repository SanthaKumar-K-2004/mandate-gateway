# RAZORPAY — Product Truth Engine Architecture (M24)

## Overview
The **Product Truth Engine** (`ProductTruthEngine` in `apps/api/commerce/product_truth_engine.py`) enforces strict validation rules ensuring that a discovered search candidate is a genuine, single SKU product with verified live pricing before any purchase proposal is generated.

## Verification Requirements
A candidate product is evaluated against 6 core truth criteria:
1. **Exact Product Detail URL (`is_exact_product_url`)**: Verifies the URL path points to a specific item page (`/product/`, `/p/`, `/item/`, `/dp/`, `.html` slug) rather than a generic collection, category, or homepage.
2. **Realistic Price Evidence**: Verifies that extracted price amount is a valid positive retail figure (`>= ₹10.00` / 1000 Paise) in `INR`.
3. **Merchant Seller Identity**: Resolves seller domain (`domain`) and legal name, distinguishing the seller from search providers (Tavily/Brave) and payment gateways.
4. **Stock Availability**: Verifies live stock availability (`is_in_stock`).
5. **Retrieval Freshness**: Preserves ISO 8601 retrieval timestamp.
6. **Cryptographic Evidence Hash**: Computes `SHA256(source_url | name | amount_paise | currency | retrieved_at)` digest.

## Fail-Closed States
- If any criterion fails, the product status is set to `UNVERIFIED` or `SOURCE_BACKED`.
- Only products meeting all 6 criteria receive `PRODUCT_VERIFIED` status and can proceed to capability resolution.
