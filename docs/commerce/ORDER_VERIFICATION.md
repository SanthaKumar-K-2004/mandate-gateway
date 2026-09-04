# RAZORPAY — Order Verification Engine (M24)

## Authoritative Order Outcome Tracking

Technical Honesty Invariant:
"HTTP 200 responses, web redirects, or payment authorizations DO NOT equal a verified order outcome."

## Order States
- `ORDER_PENDING`: Checkout intent recorded, awaiting payment execution or merchant confirmation.
- `ORDER_VERIFIED`: Authoritative order evidence (merchant order ID, SHA-256 evidence hash, connector proof) confirmed.
- `ORDER_UNKNOWN`: Payment committed or redirect completed, but merchant order confirmation is pending or unverified.
- `ORDER_FAILED`: Payment or checkout failed.
