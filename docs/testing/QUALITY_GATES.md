# Mandate Gateway — Quality Gates & CI Architecture

**Module:** M00 — Engineering Foundation  
**Section:** S00.6 — Quality Gates & CI  
**Status:** COMPLETE / FROZEN  

---

## Overview

Section **S00.6** establishes an enterprise-grade, deterministic, fail-closed Quality Gate System for Mandate Gateway. The quality system operates identically across local developer machines (`make check`) and continuous integration pipelines (`.github/workflows/quality.yml`).

---

## Quality Gate Sequence

Every build passes through 9 sequential quality gates:

```
Developer / CI
    ↓
1. make preflight          (Local environment & Compose verification)
    ↓
2. make config-check       (Fail-fast settings validation & secret redaction)
    ↓
3. make format-check       (Black style compliance check)
    ↓
4. make lint               (Flake8 static code linting)
    ↓
5. make typecheck          (Mypy static type checking)
    ↓
6. make test               (Automated unit & integration test suites)
    ↓
7. make security           (Security test suite & secret leak prevention)
    ↓
8. make secret-scan        (Repository-wide credential & sentinel scanner)
    ↓
9. make architecture-check (Architecture regression guard)
    ↓
PASS / FAIL
```

---

## Developer Command Interface

| Target | Description | Fail-Closed Policy |
|---|---|---|
| `make help` | Display available developer commands | N/A |
| `make install` | Install quality gate toolchain (`black`, `flake8`, `mypy`) | Exits non-zero on pip error |
| `make format` | Auto-format Python source files | N/A |
| `make format-check` | Verify formatting compliance (`black --check`) | Exits 1 if unformatted |
| `make lint` | Run static code linter (`flake8`) | Exits 1 on lint violations |
| `make typecheck` | Perform static type checking (`mypy`) | Exits 1 on type errors |
| `make test` | Run all unit and integration test suites | Exits 1 on test failure |
| `make security` | Run security test suite | Exits 1 on security test failure |
| `make secret-scan` | Scan repository for credentials & sentinels | Exits 1 if secret detected |
| `make architecture-check` | Enforce M00 boundary invariants | Exits 1 if prohibited code exists |
| `make config-check` | Display effective redacted settings | Exits 1 if configuration invalid |
| `make check` | Run master quality gate sequence | Exits on FIRST failed gate |
| `make clean` | Remove build artifacts & cache directories | N/A |

---

## Continuous Integration (`.github/workflows/quality.yml`)

The GitHub Actions workflow reuses repository-defined quality commands to guarantee local/CI parity.

```yaml
name: Quality Gates & CI

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

permissions:
  contents: read

jobs:
  quality-gate:
    name: Mandate Gateway Quality Gate
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install Quality Gate Toolchain
        run: |
          python -m pip install --upgrade pip
          pip install black flake8 mypy

      - name: Run Master Quality Gate (make check)
        run: |
          make check
```

---

## Failure-Injection Verification Loop (Negative Testing)

To prove every quality gate actively detects regressions and fails closed, controlled failure injections were executed:

| Quality Gate | Injected Failure | Result | Clean Recovery |
|---|---|---|---|
| **Format Check** | Unformatted Python spacing | **FAILED (exit 1)** | **PASSED (exit 0)** |
| **Lint Gate** | Unused imports (F401) | **FAILED (exit 1)** | **PASSED (exit 0)** |
| **Typecheck Gate** | Return type mismatch (`int` vs `str`) | **FAILED (exit 1)** | **PASSED (exit 0)** |
| **Test Suite** | Failing assertion (`self.assertTrue(False)`) | **FAILED (exit 1)** | **PASSED (exit 0)** |
| **Secret Scan** | Razorpay Test Key pattern (`rzp_test_...`) | **FAILED (exit 1)** | **PASSED (exit 0)** |
| **Architecture Guard** | Prohibited import (`import razorpay`) | **FAILED (exit 1)** | **PASSED (exit 0)** |

---

## Verification & Integrity Metrics

- `PROJECT_CONTEXT.md` SHA-256 Digest: `2b62d52aa707bc9bb5df60d93b04f60933562e69af8068c46cc3b6cdc2eb670a` (100% INTACT)
- Secret Scanner: **125 files scanned**, 0 unauthorized sentinels detected
- Master Test Suite: **39/39 tests PASS** (Unit + Security)
- Type Checker: `mypy` checked 29 source files with zero errors (`disallow_untyped_defs = true`)
- Linter: `flake8` checked 29 source files with zero warnings
