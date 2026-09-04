# Mandate Gateway — Final Competition & Technical Demo Script

## System: Mandate Gateway — Verified AI Commerce Agent
## Version: v2.0.0 (Agentic Payment Protocol & Razorpay Test Integration Release)

> **Disclaimer Notice**: Mandate Gateway is an independent open-source AI commerce safety project. It is **NOT** affiliated with, endorsed by, or connected to **Razorpay Software Private Limited**.

---

## 30-Second Elevator Pitch

> Mandate Gateway is a production-hardened AI commerce safety agent that solves a critical flaw in current AI assistants: it **refuses to hallucinate financial or product data**. If a price or product is unverified, it explicitly reports it. If shipping fees are unverified, it shows them as **UNKNOWN**. It provides an **Agentic Payment Protocol Layer** featuring Razorpay Test Mode (`https://api.razorpay.com/v1`), x402 HTTP 402 payment negotiation, and UAP-aligned delegated authorization. Every purchase flow requires a cryptographic single-use human confirmation token, and defense-in-depth across five enforcement layers ensures **no payment effect can ever execute twice**.

---

## 12-Phase Master Demo Flow Scenario: "Find coffee and biscuits under ₹300"

| Phase | Title | Demonstration Action & Output |
| :--- | :--- | :--- |
| **Phase 1** | **Natural Language Request** | User inputs: *"Find coffee and biscuits under ₹300."* |
| **Phase 2** | **Live Research** | Agent queries OpenFoodFacts REST API (`world.openfoodfacts.org`) for candidate products. |
| **Phase 3** | **Product Verification** | Live price, title, and ingredient evidence checked; SHA-256 evidence hashes generated. |
| **Phase 4** | **Cart Optimization** | Algorithmic optimizer evaluates combinations (e.g. Coffee ₹149 + Biscuits ₹150 = ₹299 subtotal). |
| **Phase 5** | **Unknown Fee Handling** | Subtotal ₹299 is displayed; Shipping = `UNKNOWN`, Tax = `UNKNOWN`. Zero false certainty. |
| **Phase 6** | **Razorpay Order Creation** | Generates 1:1 bound Razorpay Test Mode Order (`29900` paise) via REST API `https://api.razorpay.com/v1`. |
| **Phase 7** | **Human Authorization UI** | Itemized breakdown card displays known costs, SANDBOX mode badge, and `[CONFIRM PURCHASE]` button. |
| **Phase 8** | **Test Payment Execution** | User clicks confirm; HMAC token verified, single-use nonce consumed, payment processed. |
| **Phase 9** | **Webhook Verification** | Inbound Razorpay webhook signature (`X-Razorpay-Signature`) verified using HMAC-SHA256. |
| **Phase 10** | **Reconciliation** | Payment state mapped to `CAPTURED`; ledger reconciled idempotently (`BOTH_CONFIRMED`). |
| **Phase 11** | **Audit Trail & Timeline** | Event timeline updated with SHA-256 evidence chain; audit log written to disk. |
| **Phase 12** | **Duplicate Execution Failure Demo** | Second execution attempt using same confirmation token/idempotency key is **BLOCKED** with zero second payment effect. |

---

## 3-Minute Hackathon Demo

### Pre-Demo Check
```bash
cd /home/santhakumar/Desktop/Razorpay
make check
# Output: [✓] ALL S00.6 QUALITY GATE CHECKS PASSED CLEANLY!
```

### Stage 1 — Master Quality Gate (30s)
> "First, let's look at engineering rigor. Our master quality gate enforces linting, strict mypy type safety, 870 unit tests, 281 security tests, architecture guards, and automated secret scanning."
```bash
make check
```

### Stage 2 — Razorpay Test Mode & Protocol Integration (45s)
> "Our Agentic Payment Protocol Layer integrates Razorpay Test Mode via the official REST API in minor units (paise). It also supports x402 HTTP 402 payment requirements and UAP-aligned delegated agent authority."
```bash
PYTHONPATH=. python3 scripts/run_production_reality_certification.py
```

### Stage 3 — Autonomous MCP Execution Barrier (45s)
> "Security is built into our MCP protocol layer. While discovery tools are exposed, direct execution tools like `execute_payment` and `create_merchant_order` are strictly blocked from discovery and direct invocation."
```bash
PYTHONPATH=. python3 scripts/mcp_client_test_runner.py
```

### Stage 4 — Replay & Duplicate Prevention Attack Demo (60s)
> "Let's demonstrate our 5-layer payment replay protection. Re-using a confirmation token or submitting a duplicate idempotency key is immediately blocked, ensuring zero accidental double charges."
```bash
PYTHONPATH=. python3 -c "
from apps.api.commerce.payments.policy import AgentPaymentPolicyEngine
from apps.api.commerce.payments.models import AgentPaymentPolicy
engine = AgentPaymentPolicyEngine()
print('Policy Engine Verification Gate:', engine.evaluate_request({'amount_paise': 29900, 'product_verified': True, 'human_confirmed': True}))
"
```

---

## 5-Minute Technical Deep Dive

### Part 1: MCP Direct Call Rejection Barrier (1m)
Demonstrate that calling `execute_payment` directly via MCP returns a `Security Rejection` JSON-RPC error:
```bash
PYTHONPATH=. python3 -c "
from apps.api.agent.mcp_server import RazorpayMCPServer
server = RazorpayMCPServer()
resp = server.handle_mcp_request({
    'jsonrpc': '2.0',
    'id': 999,
    'method': 'tools/call',
    'params': {'name': 'execute_payment', 'arguments': {}}
})
print(resp)
"
```
*Expected Output*: `error: {code: -32000, message: "Security Rejection: Tool 'execute_payment' is restricted..."}`

### Part 2: Human Confirmation Gate Single-Use Token Barrier (1m)
Demonstrate that a confirmation token is consumed immediately and rejected on replay:
```bash
PYTHONPATH=. python3 -c "
from apps.api.agent.confirmation_gate import HumanConfirmationGate
gate = HumanConfirmationGate()
token_info = gate.generate_token('req_01', 'merchant_test', 'buyer_test', 29900)
token = token_info['confirmation_token']
print('Generated Token:', token)

# First verification -> SUCCESS
gate.verify_and_consume_token(token, 'req_01', 'merchant_test', 'buyer_test', 29900)
print('First Verification: CONSUMED SUCCESSFULLY')

# Second verification -> REJECTED (Replay Rejection)
try:
    gate.verify_and_consume_token(token, 'req_01', 'merchant_test', 'buyer_test', 29900)
except Exception as e:
    print('Second Verification: REJECTED ->', e)
"
```

    gate.verify_and_consume_token(token, 'req_01', 'merchant_test', 'buyer_test', 15000)
except Exception as e:
    print('Second Verification REJECTED:', e)
"
```

### Part 4: Production Chaos Matrix Suite (2m)
Run the 18-scenario chaos matrix suite:
```bash
PYTHONPATH=. python3 -m unittest tests/production/test_chaos_failure_matrix.py -v
```

---

## Fallback Plan

If live external APIs (`world.openfoodfacts.org`) experience temporary network issues or latency during a live presentation:

1. The system **fails closed safely** — it displays `SOURCE_BACKED` or `UNVERIFIED` and explicitly shows fees as `UNKNOWN`. Highlight this as proof of fail-closed security.
2. Run the offline test certification suite:
```bash
make check
PYTHONPATH=. python3 -m unittest tests/production/test_chaos_failure_matrix.py -v
```
