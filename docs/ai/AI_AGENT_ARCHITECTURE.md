# RAZORPAY — AI Agent Platform Architecture (M22)

## Overview
The RAZORPAY AI Agent Platform enables autonomous consumer and operator AI agents to interact with the RAZORPAY payment engine while strictly maintaining the core system invariant: **"NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE."**

## Non-Negotiable System Boundary
> [!IMPORTANT]
> The LLM NEVER directly authorizes or executes payments. All natural language prompts are processed through a multi-stage pipeline:
> **Intent Extraction -> Tool Discovery & Search -> Constraint Ranking -> Purchase Plan -> Cryptographic Human Confirmation Gate -> Deterministic Payment Engine**.

```
+-------------------+      +--------------------+      +--------------------+
|  User AI Prompt   | ---> |   LLM Gateway      | ---> |   Tool Registry    |
+-------------------+      +--------------------+      +--------------------+
                                                                 |
                                                                 v
+-------------------+      +--------------------+      +--------------------+
| Payment Execution | <--- | Security Gateway   | <--- | Human Confirmation |
| (Domain Engine)   |      | & Audit Ledger     |      | Gate (HMAC Token)  |
+-------------------+      +--------------------+      +--------------------+
```

## Layer Components
1. **Domain Models (`apps/api/agent/models.py`)**: Typed dataclasses for `AgentRequest`, `AgentIntent`, `PurchasePlan`, `ToolInvocation`, `ToolResult`, `AgentDecision`, `ConfirmationRequirement`.
2. **LLM Provider Abstraction (`apps/api/agent/llm_gateway.py`)**: Provider gateway supporting `MockLLMProvider`, `OpenAICompatibleProvider`, and `GeminiCompatibleProvider`.
3. **Structured Output Security (`apps/api/agent/validator.py`)**: Fail-closed validator rejecting privilege injection attempts and normalizing amounts to INR Paise.
4. **AI Tool Registry (`apps/api/agent/tool_registry.py`)**: Allowlisted registry with permission classification (`SAFE_READ`, `RESTRICTED`, `CONFIRMATION_REQUIRED`).
5. **Razorpay MCP Server (`apps/api/agent/mcp_server.py`)**: Model Context Protocol JSON-RPC adapter for tool discovery and execution.
6. **Purchase Planning Engine (`apps/api/agent/purchase_planner.py`)**: Deterministic flow engine creating candidate purchase plans.
7. **Human Confirmation Gate (`apps/api/agent/confirmation_gate.py`)**: HMAC-SHA256 token authority binding request parameters and enforcing single-use replay protection.
8. **AI Security Gateway (`apps/api/agent/security_gateway.py`)**: Multi-layered defense evaluating prompt injection, IDOR attacks, and confirmation bypass attempts.
9. **AI Audit Trail (`apps/api/agent/audit.py`)**: Machine-readable audit events appended to the tamper-evident SHA-256 ledger.
10. **REST Router (`apps/api/routers/agent.py`)**: Endpoints `POST /api/agent/requests`, `GET /api/agent/requests/{id}`, `POST /api/agent/requests/{id}/confirm`.
