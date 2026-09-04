# RAZORPAY — Production Deployment Guide

## Overview
This document provides production deployment instructions for Mandate Gateway.

---

## 1. Prerequisites
- Docker v24.0+ & Docker Compose v2.20+
- Valid Domain with TLS Certificate (e.g. Let's Encrypt / Cloudflare)
- PostgreSQL 15+ & Redis 7+

---

## 2. Deployment Steps

```bash
# 1. Clone repository
git clone https://github.com/razorpay/mandate-gateway.git
cd mandate-gateway

# 2. Configure production environment
cp .env.example .env
nano .env

# Set required production secrets:
# JWT_SECRET=<secure_random_64_char_key>
# RECONCILIATION_HMAC_SECRET=<secure_random_64_char_key>
# CAFE_ACME_API_KEY=<merchant_api_key>
# POSTGRES_PASSWORD=<secure_db_password>

# 3. Validate deployment configuration
docker compose -f docker-compose.production.yml config

# 4. Launch production stack
docker compose -f docker-compose.production.yml up -d --build

# 5. Verify deployment health
curl -f https://yourdomain.com/health
```
