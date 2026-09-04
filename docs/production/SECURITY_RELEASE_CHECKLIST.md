# RAZORPAY — Security Release Checklist

## Production Security Preflight

- [x] **No Debug Mode**: `LOG_LEVEL` set to `INFO` or `WARN` in production.
- [x] **Secret Isolation**: Zero secrets committed to git. Secrets injected via environment variables.
- [x] **HTTPS Termination**: TLS 1.2+ enforced with HSTS (`max-age=63072000`).
- [x] **Secret Redaction**: Structured JSON logger redacts API keys, HMAC secrets, passwords, bearer tokens, and payment card numbers.
- [x] **Fail-Closed Policy**: Invalid requests, expired tokens, or unverified live evidence fail closed.
- [x] **Core Invariant Preserved**: `"NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE."`
