"""
S02.1 / S02.2 — Tool Error Codes & Exception Hierarchy.

Defines machine-readable error codes and domain exceptions for tool boundary failures.
"""

from __future__ import annotations

from enum import Enum


class ToolErrorCode(str, Enum):
    """Structured machine-readable tool error codes."""

    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    TOOL_DISABLED = "TOOL_DISABLED"
    CAPABILITY_DENIED = "CAPABILITY_DENIED"
    INVALID_TOOL_REQUEST = "INVALID_TOOL_REQUEST"
    INVALID_TOOL_ARGUMENTS = "INVALID_TOOL_ARGUMENTS"
    INVALID_TOOL_VERSION = "INVALID_TOOL_VERSION"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_INPUT_TOO_LARGE = "TOOL_INPUT_TOO_LARGE"
    TOOL_OUTPUT_TOO_LARGE = "TOOL_OUTPUT_TOO_LARGE"
    TOOL_INVOCATION_LIMIT = "TOOL_INVOCATION_LIMIT"
    FORBIDDEN_OPERATION = "FORBIDDEN_OPERATION"
    AUTHORITY_FIELD_REJECTED = "AUTHORITY_FIELD_REJECTED"
    UNSAFE_TARGET = "UNSAFE_TARGET"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"


class ToolExecutionError(Exception):
    """Domain error raised during tool validation or execution failure."""

    def __init__(self, code: ToolErrorCode, detail: str) -> None:
        super().__init__(f"[{code.value}] {detail}")
        self.code: ToolErrorCode = code
        self.detail: str = detail
