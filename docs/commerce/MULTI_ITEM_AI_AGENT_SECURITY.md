# RAZERPAY — Multi-Item AI Agent Security & Threat Model

## Overview
Milestone **M28** enforces strict security boundaries around autonomous multi-item research.

---

## Security Boundaries

1. **Research Gate Isolation**: Research operations (`research_shopping_request`, `optimize_cart`) are strictly `SAFE_READ`.
2. **No Automatic Payment Execution**: The AI Agent is forbidden from triggering payment authorization or order creation automatically.
3. **Cart Token Replay Prevention**: Dynamic revalidation verifies live price & stock before checkout. If changes are detected, `CART_CHANGED` is returned.
4. **Adversarial URL Filtering**: Products with non-HTTP/HTTPS URLs (e.g. `file://`, `javascript:`) are rejected.
