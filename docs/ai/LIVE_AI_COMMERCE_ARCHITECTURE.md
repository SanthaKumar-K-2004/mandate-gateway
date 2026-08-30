# RAZERPAY — Live AI Commerce Architecture (M23)

## Overview
Milestone M23 transitions the RAZERPAY AI Agent Platform from mock/demo runtime dependencies to production live integrations (OpenRouter, Gemini REST API, Tavily Live Web Search, Brave Search, and Open-Source Public Search).

The non-negotiable system invariant remains absolute:
> **"NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE."**

## End-to-End Live Purchase Flow

```
+------------------+     +-------------------+     +---------------------+
| User Request     | --> | Live LLM Provider | --> | Security Validation |
| "Buy coffee..."  |     | (OpenRouter/Gemini|     | & Intent Sanitization|
+------------------+     +-------------------+     +---------------------+
                                                              |
                                                              v
+------------------+     +-------------------+     +---------------------+
| Purchase Plan    | <-- | Product Truth     | <-- | Live Discovery      |
| & HMAC Token     |     | Validator         |     | Orchestrator        |
+------------------+     +-------------------+     +---------------------+
          |
          v
+------------------+     +-------------------+     +---------------------+
| Human            | --> | RAZERPAY Domain   | --> | Committed Payment   |
| Confirmation     |     | Authorization     |     | Execution State     |
+------------------+     +-------------------+     +---------------------+
```

## Core Security & Architecture Layers
1. **Live LLM Gateway (`apps/api/agent/llm_gateway.py`)**: Environment-driven provider (`LLM_PROVIDER`: `openrouter`, `gemini`, `openai`). Rejects `MockLLMProvider` in production runtime (`APP_ENV=production`). Secret key masking enforces zero key exposure in repr, logs, or API payloads.
2. **Live Data Discovery Orchestrator (`apps/api/agent/live_data.py`)**: Multi-provider hierarchy (`TavilyWebSearchProvider` -> `BraveWebSearchProvider` -> `OpenSourceWebSearchProvider`). Extracts product evidence, price evidence, merchant domain, and verification status.
3. **Product Truth Validator (`apps/api/agent/product_truth_validator.py`)**: Strict truth engine cross-referencing LLM recommendations against verified discovery source records. LLMs CANNOT invent products, prices, or availability.
4. **Enhanced Cryptographic Confirmation Gate (`apps/api/agent/confirmation_gate.py`)**: Issues single-use HMAC-SHA256 tokens binding `request_id + merchant_id + buyer_id + product_id + product_source + amount_paise + currency + purchase_plan_hash + expires_at`. Replays or parameter alterations are rejected with `ConfirmationError`.
5. **Payment Middleware Routing (`apps/api/routers/agent.py`)**: Confirmed purchase plans route directly through the existing RAZERPAY authorization, idempotency, risk, state machine, and append-only audit ledger (`AIAuditLogger`).
