"""
Mandate Gateway — Versioning & Release Traceability
Section M10 — Production Operations & Release Traceability
"""

from __future__ import annotations

import os
from typing import Any, Dict

RELEASE_VERSION = "1.0.0-rc1"
BUILD_COMPONENT = "mandate-gateway"


def get_git_commit_hash() -> str:
    """Return git commit hash if available in environment or git HEAD."""
    env_hash = os.getenv("GIT_COMMIT_HASH")
    if env_hash:
        return env_hash[:40]

    try:
        head_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".git", "HEAD")
        if os.path.exists(head_file):
            with open(head_file, "r") as f:
                content = f.read().strip()
            if content.startswith("ref:"):
                ref_path = os.path.join(
                    os.path.dirname(__file__), "..", "..", "..", ".git", content.split(" ")[1]
                )
                if os.path.exists(ref_path):
                    with open(ref_path, "r") as rf:
                        return rf.read().strip()[:40]
            else:
                return content[:40]
    except Exception:
        pass
    return "UNKNOWN"


def get_version_info() -> Dict[str, Any]:
    """
    Return release version metadata.
    Exposes build version and commit hash without exposing credentials or internal paths.
    """
    return {
        "version": RELEASE_VERSION,
        "component": BUILD_COMPONENT,
        "commit": get_git_commit_hash(),
    }
