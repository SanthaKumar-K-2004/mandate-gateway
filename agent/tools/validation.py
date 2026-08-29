"""
S02.2 — Tool Input/Output Schema & Authority Validation Engine.

Enforces schema validation, authority field injection defense, input size limits,
and SSRF target protection for tool invocations.
"""

from __future__ import annotations

import json
import re
from typing import Any, Set

from agent.tools.errors import ToolErrorCode, ToolExecutionError
from agent.tools.interface import CANONICAL_TOOL_NAME_REGEX

# Authority claims explicitly forbidden from untrusted tool input payloads
FORBIDDEN_AUTHORITY_INPUT_KEYS: Set[str] = {
    "authorized",
    "approved",
    "human_confirmed",
    "admin_override",
    "payment_approved",
    "skip_policy",
    "skip_mandate",
    "skip_budget",
    "skip_nonce",
    "skip_step_up",
    "bypass_auth",
    "role",
    "is_admin",
    "trusted",
    "authorization_result",
    "payment_status",
}

# SSRF and code injection unsafe patterns
PROHIBITED_TARGET_PATTERNS = [
    re.compile(r"localhost", re.IGNORECASE),
    re.compile(r"127\.0\.0\.1"),
    re.compile(r"0\.0\.0\.0"),
    re.compile(r"::1"),
    re.compile(r"169\.254\.169\.254"),
    re.compile(r"file://", re.IGNORECASE),
    re.compile(r"data://", re.IGNORECASE),
    re.compile(r"data:", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
    re.compile(r"192\.168\.\d{1,3}\.\d{1,3}"),
    re.compile(r"172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}"),
    re.compile(r"__import__"),
    re.compile(r"eval\s*\("),
    re.compile(r"exec\s*\("),
    re.compile(r"os\.system"),
    re.compile(r"subprocess"),
]


class ToolRequestValidator:
    """
    Validation engine enforcing input safety and fail-closed security rules.
    """

    @classmethod
    def validate_tool_name(cls, tool_name: str) -> None:
        """
        Validate tool identifier syntax.

        Raises ToolExecutionError if tool name is non-canonical or malicious.
        """
        if not tool_name or not tool_name.strip():
            raise ToolExecutionError(
                ToolErrorCode.INVALID_TOOL_REQUEST,
                "Tool name cannot be empty.",
            )

        norm = tool_name.strip().lower()
        if not CANONICAL_TOOL_NAME_REGEX.match(norm):
            raise ToolExecutionError(
                ToolErrorCode.INVALID_TOOL_REQUEST,
                f"Non-canonical tool identifier syntax: {tool_name!r}.",
            )

        if (
            ".." in tool_name
            or "/" in tool_name
            or "\\" in tool_name
            or "\x00" in tool_name
            or "\n" in tool_name
        ):
            raise ToolExecutionError(
                ToolErrorCode.INVALID_TOOL_REQUEST,
                f"Path traversal or control characters detected in tool name: {tool_name!r}.",
            )

        for bad in ("python:", "shell:", "exec:", "eval:", "import:", "module:"):
            if norm.startswith(bad):
                raise ToolExecutionError(
                    ToolErrorCode.INVALID_TOOL_REQUEST,
                    f"Forbidden execution prefix in tool name: {tool_name!r}.",
                )

    @classmethod
    def validate_input_payload(
        cls, tool_name: str, arguments: dict[str, Any], max_bytes: int
    ) -> None:
        """
        Validate argument size, authority field absence, and SSRF targets.
        """
        # 1. Size Limit
        try:
            raw_bytes = json.dumps(arguments).encode("utf-8")
        except Exception as e:
            raise ToolExecutionError(
                ToolErrorCode.INVALID_TOOL_ARGUMENTS,
                f"Failed to serialize tool arguments to JSON: {e}",
            )

        if len(raw_bytes) > max_bytes:
            raise ToolExecutionError(
                ToolErrorCode.TOOL_INPUT_TOO_LARGE,
                f"Tool input payload ({len(raw_bytes)} bytes) exceeds maximum limit ({max_bytes} bytes).",
            )

        # 2. Authority Field Scan
        cls._scan_authority_keys(tool_name, arguments)

        # 3. SSRF & Code Injection Scan
        cls._scan_ssrf_targets(tool_name, arguments)

    @classmethod
    def _scan_authority_keys(cls, tool_name: str, payload: Any) -> None:
        """Recursively scan payload for forbidden authority keys."""
        if isinstance(payload, dict):
            for k, v in payload.items():
                if isinstance(k, str) and k.lower() in FORBIDDEN_AUTHORITY_INPUT_KEYS:
                    raise ToolExecutionError(
                        ToolErrorCode.AUTHORITY_FIELD_REJECTED,
                        f"Forbidden authority field {k!r} detected in tool arguments for {tool_name!r}.",
                    )
                cls._scan_authority_keys(tool_name, v)
        elif isinstance(payload, list):
            for item in payload:
                cls._scan_authority_keys(tool_name, item)

    @classmethod
    def _scan_ssrf_targets(cls, tool_name: str, payload: Any) -> None:
        """Recursively scan payload strings for unsafe network target URLs or code injections."""
        if isinstance(payload, str):
            for pattern in PROHIBITED_TARGET_PATTERNS:
                if pattern.search(payload):
                    raise ToolExecutionError(
                        ToolErrorCode.UNSAFE_TARGET,
                        f"Unsafe target URL or pattern detected in tool argument for {tool_name!r}: {payload!r}.",
                    )
        elif isinstance(payload, dict):
            for k, v in payload.items():
                cls._scan_ssrf_targets(tool_name, k)
                cls._scan_ssrf_targets(tool_name, v)
        elif isinstance(payload, list):
            for item in payload:
                cls._scan_ssrf_targets(tool_name, item)
