# RAZORPAY — Production Operational Runbook

## Overview
Operational runbook for maintaining and operating Mandate Gateway in production.

---

## Service Management

### Restart Stack
```bash
docker compose -f docker-compose.production.yml restart
```

### View Application Logs
```bash
docker compose -f docker-compose.production.yml logs -f api
```

### Check Connector Health
```bash
curl -s http://localhost:8000/api/v1/commerce/connectors | jq .
```
