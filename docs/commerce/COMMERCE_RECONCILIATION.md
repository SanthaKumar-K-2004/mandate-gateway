# RAZORPAY — Commerce Transaction Reconciliation Architecture

## Overview
The `CommerceReconciliationEngine` ([`apps/api/commerce/reconciliation.py`](file:///home/santhakumar/Desktop/Razorpay/apps/api/commerce/reconciliation.py)) automatically resolves uncertain payment and order states.

---

## Reconciliation States

```text
1. BOTH_CONFIRMED          Payment authorized & Merchant Order verified.
2. PAYMENT_ONLY            Payment authorized, but order status pending (PAYMENT_SUCCESS_ORDER_UNKNOWN).
3. ORDER_ONLY              Order created, but payment status unresolved.
4. UNRESOLVED              Neither payment nor order evidence confirmed.
5. MANUAL_REVIEW_REQUIRED  Conflicting evidence detected; escalated to operations.
```

---

## Automated Resolution Workflow

1. Query payment gateway ledger (`/api/v1/payments/{tx_id}`).
2. Query merchant order ledger (`/api/v1/commerce/orders/{order_id}`).
3. Compare payment transaction ID, merchant order ID, amount, and evidence hash.
4. Update authoritative state idempotently.
