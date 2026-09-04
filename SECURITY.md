# Security Policy & Disclaimer

## Project Branding & Disclaimer Notice

> **IMPORTANT DISCLAIMER**: Mandate Gateway is an independent open-source AI commerce safety project. It is **NOT** affiliated with, endorsed by, or connected to **Razorpay Software Private Limited**.

Mandate Gateway uses internal codenames (such as `RAZORPAY`) and a Razorpay-compatible MCP protocol abstraction to model financial boundaries. No live production Razorpay credentials or payment gateway accounts are used or exposed in this repository.

---

## Security Architecture Overview

Mandate Gateway enforces a deterministic fail-closed security model between untrusted AI agent runtimes and payment execution boundaries.

### Core Security Invariant
> **NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE.**

### Security Controls & Layers
1. **Human Confirmation Barrier**: Every payment or order execution requires an explicit single-use HMAC-SHA256 confirmation token.
2. **Autonomous Tool Blocking**: Direct execution tools (`execute_payment`, `create_merchant_order`, `execute_confirmed_purchase`) are filtered from MCP `tools/list` and blocked at `tools/call` invocation.
3. **Secret Redaction**: Automated logging filters redact API keys, Bearer tokens, passwords, and authorization headers from standard output and audit files.
4. **SSRF & Handoff Protection**: `GenericWebCheckoutConnector` rejects loopback addresses (`127.0.0.1`, `localhost`), internal private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), cloud metadata services (`169.254.169.254`), non-HTTP schemes (`file:`, `javascript:`, `data:`), and userinfo credentials.
5. **Fail-Closed Product Truth**: Unverified product data returns `UNVERIFIED` / `SOURCE_BACKED` and blocks checkout execution.
6. **Immutable Audit Ledger**: Ed25519-signed action receipts (`action_receipt.json`) + SHA-256 evidence hash-chain tracking.

---

## Reporting Vulnerabilities

If you discover a security vulnerability or security design flaw in Mandate Gateway:

1. **Do NOT open a public GitHub issue.**
2. Send a confidential report detailing the vulnerability, steps to reproduce, and impact to the project maintainers.
3. Provide details on:
   - Affected module or endpoint
   - Proof-of-concept exploit or workflow
   - Expected vs actual behavior
4. Maintainers will review and respond within 48 hours to confirm receipt and provide a remediation timeline.

---

## Credentials & Secrets Policy

- **Zero Hardcoded Secrets**: This repository does not contain production API keys, passwords, or live tokens.
- **Environment Isolation**: `.env.example` provides development placeholders only. Production deployments require secure secrets injected via environment variables or secret managers.
