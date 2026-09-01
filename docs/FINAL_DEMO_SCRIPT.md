# RAZERPAY — Final Demo Script

## System: Mandate Gateway — AI Commerce Agent
## Version: v1.0.0

---

## 30-Second Elevator Pitch

> RAZERPAY is a production-grade AI commerce agent that does what no existing shopping assistant does honestly: it tells you when it **doesn't know** the price, when a product is **unverified**, and refuses to place an order until **you personally confirm** it. Every product fact is sourced from live APIs. Every payment is protected by cryptographic single-use tokens and five independent duplicate-payment prevention mechanisms. It is the only AI shopping agent that is genuinely **fail-closed by design**.

---

## 3-Minute Hackathon Demo

### Setup (Before Presenting)
```bash
cd /home/santhakumar/Desktop/Razorpay
source .venv/bin/activate  # or your virtualenv
make check                  # confirm green
PYTHONPATH=. python3 scripts/run_production_reality_certification.py
```

### Step 1 — System Introduction (30 sec)
> "This is RAZERPAY — an AI commerce agent with production-grade safety guarantees. Let me show you what makes it different."

Show the quality gate:
```bash
make check
# Expected: [✓] ALL S00.6 QUALITY GATE CHECKS PASSED CLEANLY!
#           844 tests, 0 failures
```

### Step 2 — Live Product Discovery (45 sec)
```bash
PYTHONPATH=. python3 scripts/run_live_cart_research_pilot.py
```

Point out:
- The system queries **real OpenFoodFacts API** (live HTTP)
- It shows `SOURCE_BACKED` or `PRODUCT_VERIFIED` — **never invented data**
- If the provider is down: "fail-closed — the product remains UNVERIFIED and checkout is blocked"

### Step 3 — Production Reality Certification (45 sec)
```bash
PYTHONPATH=. python3 scripts/run_production_reality_certification.py
```

Walk through each stage:
1. `[✓] Production security validator` — no config issues
2. `[✓] Real connectors classified` — LIVE vs SANDBOX, no fake success paths
3. `[✓] External data provenance verified` — live OpenFoodFacts connectivity
4. `[✓] MCP Security Policy Enforcement` — 13 tools exposed; `create_merchant_order` BLOCKED
5. `[✓] Prometheus metrics operational` — observability working
6. `[✓] Fail-closed reconciliation` — PAYMENT_ONLY → manual review required

### Step 4 — Chaos Failure Matrix (30 sec)
```bash
PYTHONPATH=. python3 -m unittest tests/production/test_chaos_failure_matrix.py -v 2>&1 | tail -20
```

Say: "All 18 production failure scenarios pass: provider timeouts, circuit breakers, duplicate payments, webhook forgery, partial network failures, reconciliation recovery."

---

## 5-Minute Technical Demo

### Part 1: Architecture Walk (1 min)
Show `docs/FINAL_ARCHITECTURE.md`

Key points:
- AI agent layer → MCP protocol → tool registry
- ProductTruthEngine — NEVER invents data
- 5 independent duplicate-payment prevention mechanisms
- Full observability stack (Prometheus + Grafana)

### Part 2: Live API Connectivity (1 min)
```bash
PYTHONPATH=. python3 -c "
from apps.api.commerce.connectors.public_platform import PublicPlatformConnector
conn = PublicPlatformConnector()
print('Connector ID:', conn.connector_id)
print('Capability:', conn.capability.value)
result = conn.search_products({'query': 'coffee'})
print('Products found:', len(result.get('products', [])))
print('Source:', result.get('source_domain'))
"
```

### Part 3: Product Truth Engine (1 min)
```bash
PYTHONPATH=. python3 -c "
from apps.api.commerce.product_truth_engine import ProductTruthEngine
truth = ProductTruthEngine.evaluate_product({
    'product_id': 'demo_coffee',
    'source_url': 'https://world.openfoodfacts.org/product/20000001',
})
print('Verified:', truth.is_sku_verified)
print('Price verified:', truth.is_price_verified)
print('Status:', truth.product.verification_status.value)
print('Validation errors:', truth.validation_errors or 'None')
"
```

Show: If URL is invalid/unreachable → `UNVERIFIED` → checkout blocked.

### Part 4: Human Confirmation Gate (1 min)
```bash
PYTHONPATH=. python3 -c "
from apps.api.agent.confirmation_gate import HumanConfirmationGate
gate = HumanConfirmationGate()
token_info = gate.generate_token(
    request_id='demo_req_001',
    merchant_id='cafeacme_local',
    buyer_id='demo_user',
    amount_paise=18500,
)
print('Token:', token_info['confirmation_token'])
print('Status:', token_info['status'])

# First use — succeeds
try:
    gate.verify_and_consume_token(
        confirmation_token=token_info['confirmation_token'],
        request_id='demo_req_001',
        merchant_id='cafeacme_local',
        buyer_id='demo_user',
        amount_paise=18500,
    )
    print('First verify: SUCCESS (token consumed)')
except Exception as e:
    print('First verify failed:', e)

# Second use — REPLAY REJECTED
try:
    gate.verify_and_consume_token(
        confirmation_token=token_info['confirmation_token'],
        request_id='demo_req_001',
        merchant_id='cafeacme_local',
        buyer_id='demo_user',
        amount_paise=18500,
    )
    print('Second verify: SUCCESS (BUG — should not reach here!)')
except Exception as e:
    print('Second verify: REJECTED —', type(e).__name__, '(correct behavior)')
"
```

### Part 5: MCP Security Policy (30 sec)
```bash
PYTHONPATH=. python3 -c "
from apps.api.agent.mcp_server import RazerpayMCPServer
server = RazerpayMCPServer()
resp = server.handle_mcp_request({'method': 'tools/list', 'id': 1})
tools = resp['result']['tools']
names = [t['name'] for t in tools]
print('MCP tools exposed:', len(tools))
print('execute_payment exposed?', 'execute_payment' in names)
print('create_merchant_order exposed?', 'create_merchant_order' in names)
print()
print('Exposed tools:')
for n in sorted(names): print(' -', n)
"
```

Expected: Both dangerous tools are **NOT in the list**.

### Part 6: Reconciliation Fail-Closed (30 sec)
```bash
PYTHONPATH=. python3 -c "
from apps.api.commerce.reconciliation import CommerceReconciliationEngine
engine = CommerceReconciliationEngine()
record = engine.reconcile_transaction(
    purchase_request_id='demo_req_001',
    payment_transaction_id='tx_demo_001',
    merchant_id='cafeacme_local',
    buyer_id='demo_user',
    amount_paise=18500,
    payment_ledger_status='SUCCESS',
    merchant_ledger_status='UNKNOWN',
)
print('State:', record.state.value)
print('Payment verified:', record.payment_verified)
print('Order verified:', record.order_verified)
print('Evidence hash:', record.evidence_hash[:16], '...')
"
```

Expected: `PAYMENT_ONLY` — payment confirmed, order unknown → manual review required, **no double payment possible**.

---

## Fallback Plan (If OpenFoodFacts Unavailable)

If `world.openfoodfacts.org` is unreachable during the demo:

1. The system **correctly returns** `SOURCE_BACKED` or `UNVERIFIED` — do NOT hide this
2. Say: "This demonstrates the fail-closed behavior — when live data is unavailable, the system refuses to proceed rather than inventing data."
3. Show the test suite instead:
   ```bash
   PYTHONPATH=. python3 -m unittest tests/production/test_chaos_failure_matrix.py -v 2>&1 | tail -20
   ```
4. Run the certification script — Stage 3 will show "SOURCE EVALUATED (UNVERIFIED)" which is the correct honest result

---

## Demo Commands Reference Card

```bash
# Quality gate
make check

# Production certification (all 7 stages)
PYTHONPATH=. python3 scripts/run_production_reality_certification.py

# Live cart research (multi-item, real OpenFoodFacts)
PYTHONPATH=. python3 scripts/run_live_cart_research_pilot.py

# MCP client interoperability
PYTHONPATH=. python3 scripts/mcp_client_test_runner.py

# Chaos failure matrix (18 scenarios)
PYTHONPATH=. python3 -m unittest tests/production/test_chaos_failure_matrix.py -v

# Secret redaction tests
PYTHONPATH=. python3 -m unittest tests/production/test_secret_redaction.py -v

# Full test suite
PYTHONPATH=. python3 -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -5
```

---

## Key Talking Points

1. **Real data, not mock data** — OpenFoodFacts live API, no synthetic products
2. **Honest about unknowns** — shipping/tax shown as UNKNOWN, not invented
3. **Fail-closed, not fail-open** — unverified product = checkout blocked
4. **5 independent payment safety mechanisms** — not a single point of failure
5. **844 tests, 0 failures** — fully verified production state
6. **MCP security policy enforced** — dangerous tools blocked from autonomous clients
7. **Production ops ready** — Prometheus, Grafana, structured logging, incident engine
