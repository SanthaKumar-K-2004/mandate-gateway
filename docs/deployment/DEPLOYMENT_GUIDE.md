# Mandate Gateway — Deployment Architecture & Operations Guide

## Overview

Mandate Gateway supports three explicit runtime environments:
- **`development`**: Local developer sandbox with hot reloading and local Docker Compose services.
- **`staging`**: Pre-production integration environment with staging database, Redis, and simulated provider sandbox.
- **`production`**: Production environment with strict fail-closed configuration validation, non-root container isolation, encrypted secrets, and multi-process worker topology.

---

## Conceptual Topology

```
                  ┌──────────────────────┐
                  │    Reverse Proxy     │
                  │   (Nginx / Traefik)  │
                  └──────────┬───────────┘
                             │ (HTTP / gRPC)
                  ┌──────────▼───────────┐
                  │     API Service      │
                  │   (ASGI Runtime)     │
                  └─────┬──────────┬─────┘
                        │          │
         ┌──────────────┴─┐      ┌─┴──────────────┐
         │ PostgreSQL 16  │      │    Redis 7     │
         │  (Persisted)   │      │  (Cache/Locks) │
         └──────▲─────────┘      └────────▲───────┘
                │                         │
     ┌──────────┴─────────────────────────┴──────────┐
     │                                               │
┌────┴────────────────────────┐   ┌──────────────────┴──────────┐
│    Outbox Worker Process    │   │   Recovery Worker Process   │
│ (Transactional Dispatcher)  │   │  (Reconciliation Scanner)   │
└─────────────────────────────┘   └─────────────────────────────┘
```

---

## Environment Configuration

| Key | Description | Default (Dev) | Production Requirement |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | Application environment (`development`, `staging`, `production`) | `development` | Explicitly set to `production` |
| `POSTGRES_HOST` | Database host | `127.0.0.1` | Must be explicit container/DNS host |
| `POSTGRES_PORT` | Database port | `5432` | Must be valid port integer |
| `POSTGRES_DB` | Database name | `mandate_gateway` | Must be explicit database name |
| `POSTGRES_USER` | Database user | `postgres` | Must be explicit non-root user |
| `POSTGRES_PASSWORD` | Database password | `CHANGE_ME_LOCAL_ONLY` | **MUST NOT** be default/weak value |
| `REDIS_HOST` | Redis host | `127.0.0.1` | Must be explicit Redis host |
| `LOG_LEVEL` | Logging level | `INFO` | **MUST NOT** be `DEBUG` in production |
| `DEMO_MODE` | Safe live demo flag | `false` | `false` in production |

---

## Deployment Commands

### Local Development
```bash
docker-compose up -d
make check
```

### Production Deployment
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```
