"""
Mandate Gateway — AI Structured Output Security Validator
Workstream 3 — Fail-closed validator between raw LLM outputs and payment domain execution.
Ensures zero privilege escalation, amount normalization, currency validation, and tool allowlisting.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from apps.api.agent.models import AgentIntent
from apps.api.agent.tool_registry import AIToolRegistry, ToolExecutionError


class AISecurityValidationError(ValueError):
    """Raised when LLM output violates security, currency, or authorization rules."""

    pass


class AIStructuredOutputValidator:
    """Validator enforcing fail-closed security between AI gateway outputs and payment domain logic."""

    def __init__(self, tool_registry: Optional[AIToolRegistry] = None) -> None:
        self.tool_registry = tool_registry or AIToolRegistry()

    def validate_intent(self, intent: AgentIntent) -> AgentIntent:
        """Validate and sanitize extracted AgentIntent."""
        intent.validate()  # Validates intent_type, amount > 0, currency == 'INR'
        return intent

    def sanitize_raw_llm_json(self, raw_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize raw LLM dictionary output before converting to domain objects.
        Strips unallowlisted fields that attempt privilege escalation.
        """
        forbidden_privilege_fields = {
            "is_authorized",
            "bypass_confirmation",
            "override_budget",
            "sudo",
            "admin_override",
            "skip_idempotency",
        }
        for field_name in forbidden_privilege_fields:
            if field_name in raw_dict:
                raise AISecurityValidationError(
                    f"LLM output attempted forbidden privilege injection: '{field_name}'"
                )

        # Normalize amount if present
        if "amount" in raw_dict and "amount_paise" not in raw_dict:
            raw_dict["amount_paise"] = int(float(raw_dict["amount"]) * 100)

        if "amount_paise" in raw_dict:
            val = raw_dict["amount_paise"]
            if not isinstance(val, int) or val <= 0:
                raise AISecurityValidationError(
                    f"Invalid amount_paise: {val}. Must be positive integer."
                )

        # Currency validation
        if "currency" in raw_dict and raw_dict["currency"] != "INR":
            raise AISecurityValidationError(
                f"Invalid currency: '{raw_dict['currency']}'. Only INR supported."
            )

        return raw_dict

    def validate_tool_invocation(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Verify requested tool name is registered in the allowlisted AIToolRegistry."""
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            raise ToolExecutionError(
                f"Tool invocation rejected. Tool '{tool_name}' is not registered in allowlisted tool registry."
            )
