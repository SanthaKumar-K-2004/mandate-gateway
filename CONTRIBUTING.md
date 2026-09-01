# Contributing to Mandate Gateway

Thank you for your interest in contributing to **Mandate Gateway — AI Commerce Safety Agent**.

---

## Code Quality Invariants

Before submitting any Pull Request, ensure your changes satisfy all quality gates:

1. **Master Quality Gate**: Run `make check` locally. All checks (`black`, `flake8`, `mypy`, architecture regression guard, security secret scan, unit test suite) MUST pass with zero errors.
2. **Fail-Closed Security Invariant**: Never weaken financial safety barriers, confirmation gate tokens, or permission checks.
3. **No Synthetic / Mock Shortcuts**: Ensure external data connectors explicitly classify live, sandbox, or handoff capabilities.

---

## Development Workflow

```bash
# 1. Fork and clone repository
git clone https://github.com/SanthaKumar-K-2004/mandate-gateway.git
cd mandate-gateway

# 2. Setup virtualenv & install dependencies
python3 -m venv .venv
source .venv/bin/activate
make install

# 3. Format code
make format

# 4. Run quality gate
make check
```

---

## Submitting Pull Requests

- Keep commits concise and descriptive.
- Include unit tests for any new logic or bug fixes.
- Ensure `PROJECT_CONTEXT.md` remains unchanged.
