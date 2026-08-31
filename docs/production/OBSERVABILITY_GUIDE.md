# RAZERPAY — Observability Guide

## Overview
Mandate Gateway exposes Prometheus metrics at `GET /metrics` and structured JSON logs.

---

## Metrics Endpoints

- Prometheus Scrape URL: `http://localhost:8000/metrics`
- Grafana Dashboards URL: `http://localhost:3000` (Default login: `admin`)

---

## Grafana Dashboards

1. **Production Overview**: API request rate, latency, 5xx error rates.
2. **AI Agent Operations**: Research ops count, rejections, LLM errors.
3. **Commerce Connector Health**: Request rate, latency, circuit breaker state per connector.
4. **Payment Safety**: Confirmation attempts, duplicate rejections, idempotency conflicts.
5. **Reconciliation Operations**: Mismatch rejections, unresolved transaction backlog.
