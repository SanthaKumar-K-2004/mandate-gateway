# RAZERPAY — Model Context Protocol (MCP) Integration Guide (M22)

## Introduction
RAZERPAY exposes an allowlisted set of Model Context Protocol (MCP) compatible tools allowing external AI agent clients (e.g. Claude Desktop, Cursor, Custom Agents) to safely inspect catalog products, check buyer budget status, query transaction state, and formulate purchase plans.

## Supported MCP JSON-RPC Methods

### 1. `tools/list`
Lists approved allowlisted tools. Direct payment execution (`execute_payment`) is excluded from autonomous discovery.

#### Sample Request
```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 1
}
```

#### Sample Response
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "search_products",
        "description": "Search available product catalog under a maximum budget limit.",
        "inputSchema": { "type": "object", "properties": { "query": { "type": "string" }, "max_price_paise": { "type": "integer" } } }
      },
      {
        "name": "get_budget_status",
        "description": "Check buyer mandate daily budget status.",
        "inputSchema": { "type": "object", "properties": { "mandate_id": { "type": "string" } } }
      }
    ]
  }
}
```

### 2. `tools/call`
Executes an allowlisted tool with arguments.

#### Sample Request
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search_products",
    "arguments": { "query": "coffee", "max_price_paise": 20000 }
  },
  "id": 2
}
```

## Security & Permission Tiers
- `SAFE_READ`: Product search, product details, budget check, transaction status. Available to autonomous agents via MCP.
- `RESTRICTED`: Purchase plan creation. Available to autonomous agents via MCP.
- `CONFIRMATION_REQUIRED`: Payment execution (`execute_payment`). Prohibited from direct autonomous MCP execution without valid human confirmation token context.
