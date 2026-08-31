# RAZERPAY — External Model Context Protocol (MCP) Interoperability Guide

## Overview
Razerpay exposes its AI commerce and protection tools via the standard Model Context Protocol (MCP) over JSON-RPC 2.0.

---

## MCP Server Security Rules

1. **Autonomous Direct Payment Tool Exclusion**:
   - `execute_payment` and `execute_confirmed_purchase` are strictly **EXCLUDED** from `tools/list` discovery.
   - External LLMs or MCP clients can search, evaluate, and prepare checkouts, but CANNOT execute payments without an explicit, cryptographically signed human confirmation token.

2. **Supported Protocol Methods**:
   - `tools/list`: Lists available tools, input JSON schemas, and descriptions.
   - `tools/call`: Executes specified tool with validated arguments.

---

## Example JSON-RPC 2.0 Interoperability Sequences

### 1. Tool Discovery (`tools/list`)
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

### 2. Search Live Products (`tools/call`)
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search_products",
    "arguments": {
      "query": "coffee",
      "max_price_paise": 20000
    }
  }
}
```

### 3. Check Connector Health (`tools/call`)
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "get_connector_health",
    "arguments": {}
  }
}
```

---

## Interoperability Verification Script
Execute standard MCP client test runner:
```bash
PYTHONPATH=. python3 scripts/mcp_client_test_runner.py
```
