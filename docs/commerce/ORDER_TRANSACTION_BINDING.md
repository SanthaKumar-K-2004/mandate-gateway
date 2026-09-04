# RAZORPAY — Cart, Order & Payment Binding Architecture (M25)

## Overview
To prevent product substitution attacks (e.g. confirming cheap Product A but ordering expensive Product B) and payment-order mismatch, RAZORPAY implements cryptographic order binding and strict 1:1 transaction binding.

## Cryptographic Order Binding (`CommerceOrderBinder`)
Computes `order_binding_hash`:
```text
HMAC-SHA256(secret, purchase_request_id | merchant_id | buyer_id | product_id | quantity | amount_paise | currency | merchant_order_id | payment_reference | plan_hash)
```

## 1:1 Payment ↔ Merchant Order Binding (`CommerceTransactionBindingManager`)
- Strict invariant: `1 PAYMENT ↔ 1 MERCHANT ORDER BINDING`.
- Rejects duplicate transaction bindings or re-use of transaction IDs across multiple orders.
