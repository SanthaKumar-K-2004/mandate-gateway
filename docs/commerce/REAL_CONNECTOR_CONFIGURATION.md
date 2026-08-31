# RAZERPAY — Real Merchant Connector Configuration Guide

## Overview
Merchant connectors are dynamically configured via environment variables.

---

## Environment Variables

```env
# Master Commerce Connector Feature Flag
COMMERCE_CONNECTORS_ENABLED=true

# Merchant Connector 1 (Sandbox Demo)
MERCHANT_CONNECTOR_1_ENABLED=true
MERCHANT_CONNECTOR_1_BASE_URL=https://api.cafeacme.local
MERCHANT_CONNECTOR_1_API_KEY=key_cafeacme_live_m26
MERCHANT_CONNECTOR_1_WEBHOOK_SECRET=whsec_cafe_acme_live_m25
MERCHANT_CONNECTOR_1_ENVIRONMENT=SANDBOX

# Merchant Connector 2 (Public Catalog API)
MERCHANT_CONNECTOR_2_ENABLED=true
MERCHANT_CONNECTOR_2_BASE_URL=https://world.openfoodfacts.org
MERCHANT_CONNECTOR_2_API_KEY=public_catalog_key
MERCHANT_CONNECTOR_2_WEBHOOK_SECRET=whsec_m26_pilot
MERCHANT_CONNECTOR_2_ENVIRONMENT=LIVE
```

---

## Security Guidelines

- `.env` must remain gitignored.
- Placeholders only in `.env.example`.
- Credential fields are automatically redacted (`to_safe_dict()`) when returned over management APIs or rendered on the dashboard.
