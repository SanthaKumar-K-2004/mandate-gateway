# RAZORPAY — Model Context Protocol (MCP) Live Integration Guide (M23)

## Exposed MCP Tools & Permission Matrix

External AI clients (Claude Desktop, Cursor, Custom AI Agents) interact with RAZORPAY via the MCP adapter (`RazorpayMCPServer` in `apps/api/agent/mcp_server.py`).

| Tool Name | Permission Tier | Description | Discovery (`tools/list`) |
|---|---|---|---|
| `search_products` | `SAFE_READ` | Search live product catalog under budget. | Yes |
| `get_product_details` | `SAFE_READ` | Fetch details for a product ID. | Yes |
| `get_budget_status` | `SAFE_READ` | Check daily mandate budget remaining. | Yes |
| `get_transaction_status` | `SAFE_READ` | Query execution status of a transaction ID. | Yes |
| `create_purchase_plan` | `RESTRICTED` | Formulate candidate purchase plan. | Yes |
| `request_purchase_confirmation` | `RESTRICTED` | Request human confirmation token for plan. | Yes |
| `execute_confirmed_purchase` | `CONFIRMATION_REQUIRED` | Execute payment for approved proposal. | Excluded from autonomous `tools/list` |

## Security Rules
- Direct autonomous payment execution without human confirmation context is prohibited.
- `execute_confirmed_purchase` is filtered from `tools/list` discovery and requires a valid, single-use, unexpired HMAC confirmation token.
