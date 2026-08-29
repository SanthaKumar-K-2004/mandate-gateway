"""
S02.1 / S02.2 — Tool Boundary Specification & Interfaces.

Defines ToolDefinition, ToolResult, and ToolInterface contracts.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Set

from agent.tools.capabilities import FORBIDDEN_CAPABILITIES, ToolCapability
from agent.tools.errors import ToolErrorCode
from apps.api.domain.types import McpOperation

# Canonical tool name identifier regex: lowercase alphanumeric, dot, colon, hyphen, underscore
CANONICAL_TOOL_NAME_REGEX = re.compile(r"^[a-z0-9_\-\.:]+$")


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Capability declaration and schema contract for an agent tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    version: str = "1.0.0"
    capabilities: Set[ToolCapability] = field(default_factory=lambda: {ToolCapability.PRODUCT_READ})
    allowed_operations: Set[McpOperation] = field(
        default_factory=lambda: {McpOperation.CREATE_ORDER}
    )
    is_trusted: bool = False
    is_blocked_by_default: bool = False
    max_input_bytes: int = 64 * 1024  # 64 KB
    max_output_bytes: int = 256 * 1024  # 256 KB
    max_invocations: int = 5
    timeout_seconds: float = 5.0
    is_deterministic: bool = True
    has_external_io: bool = False
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Tool name cannot be empty.")

        norm_name = self.name.strip().lower()
        if not CANONICAL_TOOL_NAME_REGEX.match(norm_name):
            raise ValueError(
                f"Invalid canonical tool name {self.name!r}. "
                "Tool names must be lowercase alphanumeric with dots, hyphens, colons, or underscores."
            )

        # Path traversal & dangerous character checks
        if (
            ".." in self.name
            or "/" in self.name
            or "\\" in self.name
            or "\x00" in self.name
            or "\n" in self.name
        ):
            raise ValueError(
                f"Tool name {self.name!r} contains forbidden path or control characters."
            )

        # Rejection of dangerous prefix/execution patterns
        for bad_prefix in ("python:", "shell:", "exec:", "eval:", "import:", "module:"):
            if norm_name.startswith(bad_prefix):
                raise ValueError(f"Tool name {self.name!r} contains dangerous execution prefix.")

        # Guard against forbidden payment/admin capability registration
        for cap in self.capabilities:
            cap_val = cap.value if hasattr(cap, "value") else str(cap)
            if cap_val in FORBIDDEN_CAPABILITIES or cap in FORBIDDEN_CAPABILITIES:
                raise ValueError(
                    f"Tool {self.name!r} cannot register forbidden capability {cap!r}."
                )

        if self.max_input_bytes <= 0:
            raise ValueError("max_input_bytes must be > 0.")
        if self.max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be > 0.")
        if self.max_invocations <= 0:
            raise ValueError("max_invocations must be > 0.")
        if self.timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be > 0.0.")


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Standardized tool execution outcome."""

    tool_name: str
    success: bool
    version: str = "1.0.0"
    data: dict[str, Any] = field(default_factory=dict)
    error_code: ToolErrorCode | None = None
    error_message: str | None = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=_utc_now)


class ToolInterface(ABC):
    """Abstract tool execution interface."""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the capability definition for this tool."""
        pass

    @abstractmethod
    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """
        Execute tool logic with structured arguments.

        Must return a ToolResult without raising unhandled internal exceptions.
        """
        pass
