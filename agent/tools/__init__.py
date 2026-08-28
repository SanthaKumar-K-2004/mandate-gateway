"""
S02.1 / S02.2 — Agent Tools Package.
"""

from agent.tools.capabilities import CapabilityPolicy, FORBIDDEN_CAPABILITIES, ToolCapability
from agent.tools.errors import ToolErrorCode, ToolExecutionError
from agent.tools.interface import ToolDefinition, ToolInterface, ToolResult
from agent.tools.observability import ToolAuditLogger
from agent.tools.registry import ToolRegistry
from agent.tools.validation import ToolRequestValidator

__all__ = [
    "CapabilityPolicy",
    "FORBIDDEN_CAPABILITIES",
    "ToolCapability",
    "ToolErrorCode",
    "ToolExecutionError",
    "ToolDefinition",
    "ToolInterface",
    "ToolResult",
    "ToolAuditLogger",
    "ToolRegistry",
    "ToolRequestValidator",
]
