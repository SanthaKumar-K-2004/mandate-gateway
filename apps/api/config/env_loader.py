"""
Mandate Gateway — Environment File (.env) Loader
Section S00.3 — Configuration & Secrets Management
"""

import os
from typing import Dict


def load_env_file(filepath: str) -> Dict[str, str]:
    """
    Parses a key=value .env file safely without code evaluation or external process execution.
    Handles quote stripping, comments, inline comments, export prefixes, CRLF line endings, and Unicode.
    """
    env_vars: Dict[str, str] = {}
    if not os.path.isfile(filepath):
        return env_vars

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            # Strip trailing CRLF/newlines and leading/trailing whitespace
            stripped = line.rstrip("\r\n").strip()

            # Ignore empty lines and comment lines
            if not stripped or stripped.startswith("#"):
                continue

            # Strip bash 'export ' prefix if present
            if stripped.startswith("export "):
                stripped = stripped[7:].strip()

            if "=" in stripped:
                key, val = stripped.split("=", 1)
                key = key.strip()
                val = val.strip()

                # Handle inline comments if value is not enclosed in matching quotes
                if "#" in val:
                    is_double_quoted = len(val) >= 2 and val.startswith('"') and val.endswith('"')
                    is_single_quoted = len(val) >= 2 and val.startswith("'") and val.endswith("'")
                    if not (is_double_quoted or is_single_quoted):
                        val = val.split("#", 1)[0].strip()

                # Strip surrounding double or single quotes if present (only if length >= 2)
                if len(val) >= 2:
                    if (val.startswith('"') and val.endswith('"')) or (
                        val.startswith("'") and val.endswith("'")
                    ):
                        val = val[1:-1]

                if key:
                    env_vars[key] = val

    return env_vars
