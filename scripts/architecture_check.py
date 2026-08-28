#!/usr/bin/env python3
"""
Mandate Gateway — Architecture Guard
Section S00.6 — Quality Gates & CI

Enforces M00 Engineering Foundation boundaries.
Detects premature implementation of Razorpay SDKs, MCP servers, AI agents,
payment engines, merchant/buyer mandate policies, or cryptographic audit ledgers
prior to their authorized project phase.
"""

import os
import re
import sys
from typing import List, Tuple

# Prohibited module / symbol patterns during M00 Engineering Foundation phase
PROHIBITED_PATTERNS: List[Tuple[str, str]] = [
    ("Razorpay SDK Import", r"import\s+razorpay|from\s+razorpay"),
    ("Razorpay Client Init", r"razorpay\.Client\("),
    ("MCP Protocol Import", r"import\s+mcp|from\s+mcp"),
    ("AI Agent Model Calls", r"import\s+openai|import\s+anthropic|import\s+google\.generativeai"),
    ("Payment Execution Engine", r"class\s+PaymentExecutor|def\s+execute_payment"),
    ("Mandate Authorization Engine", r"class\s+MandateEngine|def\s+authorize_mandate"),
    ("Cryptographic Audit Ledger", r"class\s+AuditLedger|def\s+sign_receipt_ed25519"),
]

# Directories prohibited from containing code prior to their authorized phase
PROHIBITED_CODE_DIRS: List[str] = [
    "razorpay",
    "gateway",
    "audit",
    "redteam",
]


def check_architecture(root_dir: str = ".") -> bool:
    print("============================================================")
    print(" Mandate Gateway — Architecture Regression Guard")
    print("============================================================")

    violations_found = False
    files_checked = 0

    ignored_dirs = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".agents",
        ".mypy_cache",
    }

    # 1. Check prohibited code directories for unauthorized source files
    for code_dir in PROHIBITED_CODE_DIRS:
        target = os.path.join(root_dir, code_dir)
        if os.path.exists(target):
            for dirpath, dirnames, filenames in os.walk(target):
                dirnames[:] = [d for d in dirnames if d not in ignored_dirs]
                for f in filenames:
                    if f != ".gitkeep" and f.endswith((".py", ".js", ".ts", ".go", ".rs")):
                        rel_p = os.path.relpath(os.path.join(dirpath, f), root_dir)
                        print(
                            f"[ARCHITECTURAL VIOLATION] Premature module code found in prohibited zone: {rel_p}"
                        )
                        violations_found = True

    # 2. Check source & test files for prohibited imports/symbols
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in ignored_dirs]

        for filename in filenames:
            if not filename.endswith((".py", ".sh")):
                continue

            rel_path = os.path.relpath(os.path.join(dirpath, filename), root_dir)

            # Skip the architecture guard script itself and authorized S01.11 / S02.6 execution & audit files
            if rel_path in (
                "scripts/architecture_check.py",
                "scripts/verify_receipt.py",
                "apps/api/domain/execution_engine.py",
                "apps/api/adapters/razorpay_adapter.py",
                "apps/api/domain/tool_proxy.py",
                "apps/api/domain/audit_ledger.py",
                "apps/api/domain/audit_errors.py",
                "apps/api/domain/receipt_signer.py",
                "apps/api/domain/receipt_verifier.py",
                "agent/redteam/__init__.py",
                "agent/redteam/engine.py",
                "agent/redteam/errors.py",
                "agent/redteam/types.py",
                "agent/explainability/__init__.py",
                "agent/explainability/engine.py",
                "agent/explainability/errors.py",
                "agent/explainability/types.py",
                "apps/api/contracts/redteam.py",
                "apps/api/routers/redteam.py",
                "apps/api/contracts/explainability.py",
                "apps/api/routers/explainability.py",
                "apps/api/contracts/product.py",
                "apps/api/routers/merchants.py",
                "apps/api/routers/products.py",
                "apps/api/routers/mandates.py",
                "apps/api/routers/transactions.py",
                "apps/api/routers/audit.py",
                "tests/unit/test_execution_engine.py",
                "tests/security/test_execution_security.py",
                "tests/concurrency/test_execution_concurrency.py",
                "tests/integration/test_execution_integration.py",
                "tests/unit/test_audit_ledger.py",
                "tests/unit/test_receipt_crypto.py",
                "tests/security/test_audit_security.py",
                "tests/concurrency/test_audit_concurrency.py",
                "tests/integration/test_audit_integration.py",
                "tests/unit/test_redteam_engine.py",
                "tests/security/test_redteam_security.py",
                "tests/concurrency/test_redteam_concurrency.py",
                "tests/integration/test_redteam_integration.py",
                "tests/unit/test_explainability_engine.py",
                "tests/security/test_explainability_security.py",
                "tests/concurrency/test_explainability_concurrency.py",
                "tests/integration/test_explainability_integration.py",
                "tests/integration/test_control_center_routers.py",
                "tests/security/test_control_center_security.py",
                "tests/concurrency/test_control_center_concurrency.py",
                "agent/orchestrator/__init__.py",
                "agent/orchestrator/engine.py",
                "agent/orchestrator/errors.py",
                "agent/orchestrator/types.py",
                "apps/api/routers/orchestrator.py",
                "tests/unit/test_orchestrator_engine.py",
                "tests/security/test_orchestrator_security.py",
                "tests/concurrency/test_orchestrator_concurrency.py",
                "tests/integration/test_orchestrator_integration.py",
                "agent/security/__init__.py",
                "agent/security/engine.py",
                "agent/security/errors.py",
                "agent/security/types.py",
                "apps/api/domain/security_hardening.py",
                "apps/api/routers/security.py",
                "tests/unit/test_security_hardening.py",
                "tests/security/test_hardening_security.py",
                "tests/concurrency/test_hardening_concurrency.py",
                "tests/integration/test_hardening_integration.py",
                "agent/submission/__init__.py",
                "agent/submission/engine.py",
                "agent/submission/errors.py",
                "agent/submission/types.py",
                "apps/api/domain/submission.py",
                "apps/api/routers/submission.py",
                "tests/unit/test_submission_readiness.py",
                "tests/security/test_submission_security.py",
                "tests/concurrency/test_submission_concurrency.py",
                "tests/integration/test_submission_integration.py",
            ):
                continue

            files_checked += 1

            try:
                with open(rel_path, "r", encoding="utf-8", errors="ignore") as file_handle:
                    content = file_handle.read()

                for name, pattern in PROHIBITED_PATTERNS:
                    if re.search(pattern, content):
                        print(f"[ARCHITECTURAL VIOLATION] {name} pattern detected in: {rel_path}")
                        violations_found = True

            except Exception as e:
                print(f"[WARNING] Could not read file {rel_path}: {e}")

    print("------------------------------------------------------------")
    print(f" Total files checked: {files_checked}")
    if violations_found:
        print("[FAIL] Architecture Guard detected premature implementation violations!")
        return False
    else:
        print("[PASS] Zero premature business logic or architectural violations detected.")
        return True


if __name__ == "__main__":
    success = check_architecture()
    sys.exit(0 if success else 1)
