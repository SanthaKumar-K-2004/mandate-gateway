# Mandate Gateway — Final Competition & Technical Demo Script

## System: Mandate Gateway — Verified AI Commerce Agent
## Version: v1.0.0 / v1.0.1 (Audit-Hardened)

> **Disclaimer Notice**: Mandate Gateway is an independent open-source AI commerce safety project. It is **NOT** affiliated with, endorsed by, or connected to **Razorpay Software Private Limited**.

---

## 30-Second Elevator Pitch

> Mandate Gateway is a production-hardened AI commerce safety agent that solves a critical flaw in current AI assistants: it **refuses to hallucinate financial or product data**. If a price or product is unverified, it explicitly reports it. If shipping fees are unverified, it shows them as **UNKNOWN**. Every purchase flow requires a cryptographic single-use human confirmation token, and defense-in-depth across five enforcement layers ensures **no payment effect can ever execute twice**.

---

## 3-Minute Hackathon Demo

### Pre-Demo Check
```bash
cd /home/santhakumar/Desktop/Razorpay
make check
# Output: [✓] ALL S00.6 QUALITY GATE CHECKS PASSED CLEANLY!
```

### Stage 1 — Master Quality Gate (30s)
> "First, let's look at engineering rigor. Our master quality gate enforces linting, strict mypy type safety across 481 files, architecture guards, and automated secret scanning."
```bash
make check
```

### Stage 2 — Live Product Intelligence & Fail-Closed Truth (45s)
> "When the AI agent researches products, it queries live catalog APIs like OpenFoodFacts. It computes SHA-256 evidence hashes and assigns verified provenance. If a URL is invalid or unreachable, the system fails closed — it marks the item UNVERIFIED and blocks checkout execution."
```bash
PYTHONPATH=. python3 scripts/run_live_cart_research_pilot.py
```

### Stage 3 — Autonomous MCP Execution Barrier (45s)
> "Security is built into our MCP protocol layer. While discovery tools are exposed, direct execution tools like `execute_payment` and `create_merchant_order` are strictly blocked from discovery and direct invocation."
```bash
PYTHONPATH=. python3 scripts/mcp_client_test_runner.py
```

### Stage 4 — Production Reality & Reconciliation (60s)
> "Finally, let's run our 7-stage Production Reality Certification suite. It validates configuration preflight, connector reality classification, live data provenance, Prometheus metrics, and fail-closed reconciliation handling."
```bash
PYTHONPATH=. python3 scripts/run_production_reality_certification.py
```

---

## 5-Minute Technical Deep Dive

### Part 1: MCP Direct Call Rejection Barrier (1m)
Demonstrate that calling `execute_payment` directly via MCP returns a `Security Rejection` JSON-RPC error:
```bash
PYTHONPATH=. python3 -c "
from apps.api.agent.mcp_server import RazerpayMCPServer
server = RazerpayMCPServer()
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

### Part 2: Generic Web Checkout SSRF Barrier (1m)
Demonstrate that `GenericWebCheckoutConnector` blocks malicious schemes, credentials, and internal subnets:
```bash
PYTHONPATH=. python3 -c "
from apps.api.commerce.connectors.generic_web import GenericWebCheckoutConnector
connector = GenericWebCheckoutConnector()
for bad_url in ['javascript:alert(1)', 'http://user:pass@evil.com', 'http://169.254.169.254/latest/meta-data', 'http://10.0.0.1/admin']:
    try:
        connector.validate_handoff_url(bad_url)
        print('FAILED TO BLOCK:', bad_url)
    except Exception as e:
        print('BLOCKED:', bad_url, '->', e)
"
```

### Part 3: Human Confirmation Gate Single-Use Token Barrier (1m)
Demonstrate that a confirmation token is consumed immediately and rejected on replay:
```bash
PYTHONPATH=. python3 -c "
from apps.api.agent.confirmation_gate import HumanConfirmationGate
gate = HumanConfirmationGate()
token_info = gate.generate_token('req_01', 'merchant_test', 'buyer_test', 15000)
token = token_info['confirmation_token']
print('Generated Token:', token)

# First verification -> SUCCESS
gate.verify_and_consume_token(token, 'req_01', 'merchant_test', 'buyer_test', 15000)
print('First Verification: CONSUMED SUCCESSFULLY')

# Second verification -> REJECTED (Replay Rejection)
try:
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
