"""
S02.1 / S02.2 — Tool Registry & Capability Authorization Execution Boundary.

Enforces capability allowlists, version resolution, argument safety, input/output limits,
and strict tool isolation.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any

from agent.tools.capabilities import FORBIDDEN_CAPABILITIES, CapabilityPolicy, ToolCapability
from agent.tools.errors import ToolErrorCode, ToolExecutionError
from agent.tools.interface import ToolDefinition, ToolInterface, ToolResult
from agent.tools.observability import ToolAuditLogger
from agent.tools.validation import ToolRequestValidator


class ToolRegistry:
    """
    Enterprise Capability Registry and Execution Boundary.

    Security Boundaries:
    1. Default DENY — Only registered, enabled tools with authorized capabilities execute.
    2. Prohibits dynamic tool creation by LLM models.
    3. Rejects code injection, SSRF URLs, authority field spoofing, and excessive payloads.
    4. Enforces thread-safe invocation accounting per session.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolInterface] = {}
        # Key: (session_id, tool_name) -> count
        self._invocation_counts: dict[tuple[str, str], int] = {}
        self._lock: threading.RLock = threading.RLock()

    def register(self, tool: ToolInterface) -> None:
        """Register a tool instance in the capability registry."""
        with self._lock:
            def_obj = tool.definition
            key = f"{def_obj.name}:{def_obj.version}"
            if key in self._tools or def_obj.name in self._tools:
                raise ValueError(
                    f"Tool {def_obj.name!r} version {def_obj.version!r} is already registered."
                )

            # Validate that tool does NOT declare forbidden capabilities
            for cap in def_obj.capabilities:
                if cap.value in FORBIDDEN_CAPABILITIES or cap in FORBIDDEN_CAPABILITIES:
                    raise ValueError(
                        f"Tool {def_obj.name!r} cannot declare forbidden capability {cap!r}."
                    )

            self._tools[def_obj.name] = tool
            self._tools[key] = tool

    def register_tool(self, tool: ToolInterface) -> None:
        """Backward compatibility helper for S02.1 interface."""
        self.register(tool)

    def unregister(self, tool_name: str, version: str | None = None) -> None:
        """Unregister a tool instance by name and optional version."""
        with self._lock:
            if version:
                key = f"{tool_name}:{version}"
                self._tools.pop(key, None)
            self._tools.pop(tool_name, None)

    def get(self, tool_name: str, version: str | None = None) -> ToolInterface | None:
        """Look up tool instance by name and optional version."""
        with self._lock:
            if version:
                key = f"{tool_name}:{version}"
                if key in self._tools:
                    return self._tools[key]
            return self._tools.get(tool_name)

        return None

    def resolve(self, tool_name: str, version: str | None = None) -> ToolInterface:
        """
        Resolve tool instance or raise ToolExecutionError(UNKNOWN_TOOL / INVALID_TOOL_VERSION).
        """
        with self._lock:
            tool = self.get(tool_name, version)
            if not tool:
                raise ToolExecutionError(
                    ToolErrorCode.UNKNOWN_TOOL,
                    f"Tool {tool_name!r} is not registered in ToolRegistry.",
                )
            if version and tool.definition.version != version:
                raise ToolExecutionError(
                    ToolErrorCode.INVALID_TOOL_VERSION,
                    f"Requested tool version {version!r} does not match registered version {tool.definition.version!r}.",
                )
            return tool

    def list_available(
        self, capability_policy: CapabilityPolicy | None = None
    ) -> list[ToolDefinition]:
        """
        Return list of registered, non-blocked tool definitions matching capability_policy.
        """
        with self._lock:
            seen = set()
            available = []
            for tool in self._tools.values():
                tdef = tool.definition
                if tdef.name in seen or not tdef.enabled or tdef.is_blocked_by_default:
                    continue
                seen.add(tdef.name)

                # Filter by capability policy if provided
                if capability_policy:
                    if not all(capability_policy.is_allowed(cap) for cap in tdef.capabilities):
                        continue

                available.append(tdef)
            return available

    def get_tool_definitions(self) -> list[ToolDefinition]:
        """Backward compatibility for S02.1 interface."""
        return self.list_available()

    def is_registered(self, tool_name: str) -> bool:
        with self._lock:
            return tool_name in self._tools

    def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        session_id: str = "default",
    ) -> ToolResult:
        """
        Backward compatibility execution method using allow_all_safe policy.
        """
        return self.authorize_and_execute(
            tool_name=tool_name,
            arguments=arguments,
            capability_policy=CapabilityPolicy.allow_all_safe(),
            session_id=session_id,
        )

    def authorize_and_execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        capability_policy: CapabilityPolicy,
        session_id: str = "default",
        version: str | None = None,
    ) -> ToolResult:
        """
        Authorize capability policy and execute tool within the strict security boundary.
        """
        ToolAuditLogger.log_event("requested", tool_name, version or "1.0.0", session_id)

        try:
            # 1. Validate Tool Identifier Syntax
            ToolRequestValidator.validate_tool_name(tool_name)

            # 2. Resolve Tool Instance
            tool = self.resolve(tool_name, version)
            tool_def = tool.definition

            # 3. Check Enabled / Blocked Status
            if not tool_def.enabled or tool_def.is_blocked_by_default:
                ToolAuditLogger.log_event(
                    "denied",
                    tool_name,
                    tool_def.version,
                    session_id,
                    error_code=ToolErrorCode.TOOL_DISABLED,
                    detail="Tool is disabled or blocked by default.",
                )
                return ToolResult(
                    tool_name=tool_name,
                    version=tool_def.version,
                    success=False,
                    error_code=ToolErrorCode.TOOL_DISABLED,
                    error_message=f"Tool {tool_name!r} is disabled or blocked by default.",
                )

            # 4. Check Capability Allowlist Policy
            for cap in tool_def.capabilities:
                if not capability_policy.is_allowed(cap):
                    ToolAuditLogger.log_event(
                        "denied",
                        tool_name,
                        tool_def.version,
                        session_id,
                        error_code=ToolErrorCode.CAPABILITY_DENIED,
                        detail=f"Capability {cap.value!r} not authorized.",
                    )
                    return ToolResult(
                        tool_name=tool_name,
                        version=tool_def.version,
                        success=False,
                        error_code=ToolErrorCode.CAPABILITY_DENIED,
                        error_message=f"Capability {cap.value!r} is not authorized for tool {tool_name!r}.",
                    )

            # 5. Check Per-Session Invocation Limits
            with self._lock:
                session_key = (session_id, tool_def.name)
                current_count = self._invocation_counts.get(session_key, 0)
                if current_count >= tool_def.max_invocations:
                    ToolAuditLogger.log_event(
                        "denied",
                        tool_name,
                        tool_def.version,
                        session_id,
                        error_code=ToolErrorCode.TOOL_INVOCATION_LIMIT,
                        detail=f"Exceeded max invocations ({tool_def.max_invocations}).",
                    )
                    return ToolResult(
                        tool_name=tool_name,
                        version=tool_def.version,
                        success=False,
                        error_code=ToolErrorCode.TOOL_INVOCATION_LIMIT,
                        error_message=f"Tool {tool_name!r} exceeded maximum allowed invocations ({tool_def.max_invocations}).",
                    )

                self._invocation_counts[session_key] = current_count + 1

            # 6. Validate Input Payload (Size, Authority Keys, SSRF)
            ToolRequestValidator.validate_input_payload(
                tool_name, arguments, tool_def.max_input_bytes
            )

        except ToolExecutionError as tee:
            ToolAuditLogger.log_event(
                "validation_failed",
                tool_name,
                version or "1.0.0",
                session_id,
                error_code=tee.code,
                detail=tee.detail,
            )
            return ToolResult(
                tool_name=tool_name,
                version=version or "1.0.0",
                success=False,
                error_code=tee.code,
                error_message=tee.detail,
            )
        except Exception as e:
            ToolAuditLogger.log_event(
                "validation_failed",
                tool_name,
                version or "1.0.0",
                session_id,
                error_code=ToolErrorCode.INVALID_TOOL_REQUEST,
                detail=str(e),
            )
            return ToolResult(
                tool_name=tool_name,
                version=version or "1.0.0",
                success=False,
                error_code=ToolErrorCode.INVALID_TOOL_REQUEST,
                error_message=f"Tool request validation failed: {e}",
            )

        # 7. Execute Tool with Timing & Output Size Validation
        ToolAuditLogger.log_event("started", tool_name, tool_def.version, session_id)
        t0 = time.monotonic()
        try:
            res = tool.execute(arguments)
            elapsed_ms = (time.monotonic() - t0) * 1000.0

            # Validate Output Payload Size
            try:
                out_bytes = len(json.dumps(res.data).encode("utf-8"))
                if out_bytes > tool_def.max_output_bytes:
                    ToolAuditLogger.log_event(
                        "failed",
                        tool_name,
                        tool_def.version,
                        session_id,
                        error_code=ToolErrorCode.TOOL_OUTPUT_TOO_LARGE,
                        detail=f"Output ({out_bytes} bytes) exceeds limit ({tool_def.max_output_bytes}).",
                    )
                    return ToolResult(
                        tool_name=tool_name,
                        version=tool_def.version,
                        success=False,
                        error_code=ToolErrorCode.TOOL_OUTPUT_TOO_LARGE,
                        error_message=f"Tool output ({out_bytes} bytes) exceeded maximum limit ({tool_def.max_output_bytes} bytes).",
                        execution_time_ms=elapsed_ms,
                    )
            except Exception:
                pass

            ToolAuditLogger.log_event(
                "completed" if res.success else "failed",
                tool_name,
                tool_def.version,
                session_id,
                duration_ms=elapsed_ms,
            )
            return ToolResult(
                tool_name=tool_name,
                version=tool_def.version,
                success=res.success,
                data=res.data,
                error_code=res.error_code,
                error_message=res.error_message,
                execution_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            ToolAuditLogger.log_event(
                "failed",
                tool_name,
                tool_def.version,
                session_id,
                error_code=ToolErrorCode.TOOL_EXECUTION_FAILED,
                detail=str(e),
                duration_ms=elapsed_ms,
            )
            return ToolResult(
                tool_name=tool_name,
                version=tool_def.version,
                success=False,
                error_code=ToolErrorCode.TOOL_EXECUTION_FAILED,
                error_message=f"Tool execution unhandled exception: {e}",
                execution_time_ms=elapsed_ms,
            )

    def reset_counts(self) -> None:
        """Reset invocation counters for testing."""
        with self._lock:
            self._invocation_counts.clear()

    @staticmethod
    def validate_target_url(url: str) -> bool:
        """Validate target URL against SSRF and prohibited patterns."""
        try:
            ToolRequestValidator.validate_argument_safety("security_test_tool", {"url": url})
            return True
        except Exception:
            return False
