# RAZORPAY — Production Known Limitations

## Technical Limitations & Boundaries

1. **Direct Merchant Order API Coverage**:
   - Universal autonomous commercial purchasing is achieved via two distinct capabilities:
     - **`VERIFIED_API`**: Direct order creation for merchants with integrated API connectors (`cafeacme.local`).
     - **`CHECKOUT_HANDOFF`**: Secure signed checkout handoff for arbitrary public web merchants (`world.openfoodfacts.org`).
   - Direct API order creation requires explicit merchant API key or OAuth2 token configuration.

2. **Dynamic Delivery Fee Verification**:
   - Live shipping and courier APIs (e.g. FedEx, BlueDart, Dunzo) require user delivery address inputs before fetching exact quotes. Unverified delivery charges are rendered as `UNKNOWN`.
