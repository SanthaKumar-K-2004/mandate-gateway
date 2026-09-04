# RAZORPAY — Live Commerce Integration Testing Policy

## Overview
RAZORPAY enforces a strict live testing policy to ensure real network calls do not execute unintended financial transactions during routine unit tests or CI/CD builds.

---

## Test Categorization

1. **Unit & Security Matrix (`tests/`)**: Runs against local models, mock sandboxes, and pure functions. Opt-in by default (`make check`).
2. **Live Integration Pilot (`scripts/run_live_commerce_pilot.py`)**: Runs opt-in live public catalog API verification (`world.openfoodfacts.org`).
3. **MCP Interoperability Suite (`scripts/mcp_client_test_runner.py`)**: Tests external client protocol compliance against local MCP server.

---

## Security Invariants

- Live tests must NEVER execute real credit card or UPI debits automatically.
- Sandbox & demo connectors are strictly isolated from production environments (`APP_ENV=production`).
