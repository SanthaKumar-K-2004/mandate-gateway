#!/usr/bin/env python3
"""
Mandate Gateway — Repository Secret Scanner
Section S00.3 — Security & Configuration Hardening

Scans repository source and configuration files for accidental credential leaks.
Uses an explicit test sentinel allowlist for security test modules.
"""

import os
import re
import sys
from typing import Dict, List, Set

# Explicit allowlist of known test sentinels in specific test files
# MUST NOT be extended to normal source/config files
TEST_SENTINEL_ALLOWLIST: Dict[str, Set[str]] = {
    "tests/security/test_secret_leak.py": {
        "TEST_SECRET_SENTINEL_DO_NOT_LEAK_987654321",
    },
    "tests/security/test_runtime_secret_leak.py": {
        "TEST_RUNTIME_SECRET_SENTINEL_DO_NOT_LEAK_987654321",
    },
    "tests/security/test_observability_security.py": {
        "TEST_OBSERVABILITY_SECRET_SENTINEL_999888777",
    },
    "scripts/secret_scan.py": {
        "TEST_SECRET_SENTINEL_DO_NOT_LEAK_987654321",
        "TEST_RUNTIME_SECRET_SENTINEL_DO_NOT_LEAK_987654321",
        "TEST_OBSERVABILITY_SECRET_SENTINEL_999888777",
    },
}

# Production credential patterns that MUST NEVER appear ANYWHERE in project source
STRICT_SECRET_PATTERNS: List[Dict[str, str]] = [
    {"name": "Razorpay Live Key", "pattern": r"rzp_live_[0-9a-zA-Z]{14,}"},
    {"name": "Razorpay Test Key", "pattern": r"rzp_test_[0-9a-zA-Z]{14,}"},
    {"name": "Stripe Live Key", "pattern": r"sk_live_[0-9a-zA-Z]{24,}"},
    {"name": "Stripe Test Key", "pattern": r"sk_test_[0-9a-zA-Z]{24,}"},
    {
        "name": "PEM Private Key",
        "pattern": r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
    },
    {
        "name": "AWS Access Key ID",
        "pattern": r"(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
    },
]

# Sensitive test sentinels (checked against allowlist)
TEST_SENTINELS = [
    "TEST_SECRET_SENTINEL_" + "DO_NOT_LEAK_987654321",
    "TEST_RUNTIME_SECRET_SENTINEL_" + "DO_NOT_LEAK_987654321",
    "TEST_OBSERVABILITY_SECRET_SENTINEL_" + "999888777",
]


def scan_repository(root_dir: str = ".") -> bool:
    print("============================================================")
    print(" Mandate Gateway — Security Secret Scanner")
    print("============================================================")

    violations_found = False
    files_scanned = 0

    # Directories to exclude from scanning (third-party agents/skills catalog, build dirs, git)
    ignored_dirs = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".agents",
    }

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filter ignored directories in-place
        dirnames[:] = [
            d for d in dirnames if d not in ignored_dirs and not d.startswith((".venv", "venv"))
        ]

        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(dirpath, filename), root_dir)

            # Skip binary files or local ignored environment files (.env)
            if rel_path.endswith((".pyc", ".png", ".jpg", ".ico", ".tar", ".gz")):
                continue
            if rel_path == ".env" or (
                rel_path.startswith(".env.") and not rel_path.endswith(".example")
            ):
                continue

            files_scanned += 1

            try:
                with open(rel_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # 1. Check strict production secret patterns (NEVER allowed anywhere)
                for pattern_info in STRICT_SECRET_PATTERNS:
                    name = pattern_info["name"]
                    pattern = pattern_info["pattern"]
                    if re.search(pattern, content):
                        print(f"[CRITICAL SECURITY ERROR] {name} pattern detected in: {rel_path}")
                        violations_found = True

                # 2. Check test sentinels against explicit allowlist
                for sentinel in TEST_SENTINELS:
                    if sentinel in content:
                        allowed_sentinels = TEST_SENTINEL_ALLOWLIST.get(rel_path, set())
                        if sentinel in allowed_sentinels:
                            print(
                                f"[INFO] Verified intentional test sentinel in allowlisted file: {rel_path}"
                            )
                        else:
                            print(
                                f"[SECURITY ERROR] Test sentinel '{sentinel}' found outside "
                                f"allowlisted test file: {rel_path}"
                            )
                            violations_found = True

            except Exception as e:
                print(f"[WARNING] Could not read file {rel_path}: {e}")

    print("------------------------------------------------------------")
    print(f" Total files scanned: {files_scanned}")
    if violations_found:
        print("[FAIL] Secret scanner detected security violations!")
        return False
    else:
        print("[PASS] Zero production secrets or unauthorized sentinels detected.")
        return True


if __name__ == "__main__":
    success = scan_repository()
    sys.exit(0 if success else 1)
