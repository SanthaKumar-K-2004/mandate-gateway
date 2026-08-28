"""
S02.2 — Tool Contract & Capability Registry Unit Tests.
"""

from typing import Any
import unittest

from agent.tools.capabilities import CapabilityPolicy, ToolCapability
from agent.tools.errors import ToolErrorCode
from agent.tools.interface import ToolDefinition, ToolInterface, ToolResult
from agent.tools.registry import ToolRegistry


class ValidProductTool(ToolInterface):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="product_lookup",
            version="1.0.0",
            description="Lookup merchant product details",
            input_schema={"product_id": "str"},
            output_schema={"name": "str", "price_paise": "int"},
            capabilities={ToolCapability.PRODUCT_READ},
            max_input_bytes=1024,
            max_output_bytes=2048,
            max_invocations=3,
        )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        pid = arguments.get("product_id", "P1")
        return ToolResult(
            tool_name="product_lookup",
            version="1.0.0",
            success=True,
            data={"product_id": pid, "name": "Test Item", "price_paise": 1500},
        )


class DisabledTestTool(ToolInterface):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="disabled_tool",
            description="Disabled test tool",
            input_schema={},
            output_schema={},
            enabled=False,
        )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(tool_name="disabled_tool", success=True)


class LargeOutputTool(ToolInterface):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="large_output",
            description="Tool producing large output",
            input_schema={},
            output_schema={},
            max_output_bytes=50,  # Small limit for testing
        )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(
            tool_name="large_output",
            success=True,
            data={"long_data": "x" * 200},
        )


class TestToolRegistryUnit(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ToolRegistry()
        self.tool = ValidProductTool()
        self.disabled_tool = DisabledTestTool()
        self.large_tool = LargeOutputTool()
        self.registry.register(self.tool)
        self.registry.register(self.disabled_tool)
        self.registry.register(self.large_tool)

    def test_registration_and_lookup(self) -> None:
        resolved = self.registry.get("product_lookup")
        self.assertIsNotNone(resolved)

        resolved_v = self.registry.get("product_lookup", "1.0.0")
        self.assertIsNotNone(resolved_v)

    def test_duplicate_registration_fails(self) -> None:
        with self.assertRaises(ValueError):
            self.registry.register(ValidProductTool())

    def test_unregistration(self) -> None:
        self.registry.unregister("disabled_tool")
        self.assertIsNone(self.registry.get("disabled_tool"))

    def test_capability_policy_authorization(self) -> None:
        # Policy allowing PRODUCT_READ
        policy = CapabilityPolicy(allowed_capabilities={ToolCapability.PRODUCT_READ})
        res = self.registry.authorize_and_execute(
            tool_name="product_lookup",
            arguments={"product_id": "P123"},
            capability_policy=policy,
        )
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("product_id"), "P123")

    def test_capability_denied(self) -> None:
        # Policy missing PRODUCT_READ capability
        policy = CapabilityPolicy(allowed_capabilities={ToolCapability.CATALOG_READ})
        res = self.registry.authorize_and_execute(
            tool_name="product_lookup",
            arguments={"product_id": "P123"},
            capability_policy=policy,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ToolErrorCode.CAPABILITY_DENIED)

    def test_disabled_tool_denied(self) -> None:
        policy = CapabilityPolicy.allow_all_safe()
        res = self.registry.authorize_and_execute(
            tool_name="disabled_tool",
            arguments={},
            capability_policy=policy,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ToolErrorCode.TOOL_DISABLED)

    def test_unknown_tool_denied(self) -> None:
        policy = CapabilityPolicy.allow_all_safe()
        res = self.registry.authorize_and_execute(
            tool_name="non_existent",
            arguments={},
            capability_policy=policy,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ToolErrorCode.UNKNOWN_TOOL)

    def test_max_invocation_limit_per_session(self) -> None:
        policy = CapabilityPolicy.allow_all_safe()
        session = "session_test_1"

        for _ in range(3):
            res = self.registry.authorize_and_execute(
                tool_name="product_lookup",
                arguments={"product_id": "P1"},
                capability_policy=policy,
                session_id=session,
            )
            self.assertTrue(res.success)

        # 4th call for session_test_1 must breach max_invocations (3)
        res4 = self.registry.authorize_and_execute(
            tool_name="product_lookup",
            arguments={"product_id": "P1"},
            capability_policy=policy,
            session_id=session,
        )
        self.assertFalse(res4.success)
        self.assertEqual(res4.error_code, ToolErrorCode.TOOL_INVOCATION_LIMIT)

    def test_input_size_limit_exceeded(self) -> None:
        policy = CapabilityPolicy.allow_all_safe()
        large_args = {"product_id": "x" * 2000}
        res = self.registry.authorize_and_execute(
            tool_name="product_lookup",
            arguments=large_args,
            capability_policy=policy,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ToolErrorCode.TOOL_INPUT_TOO_LARGE)

    def test_output_size_limit_exceeded(self) -> None:
        policy = CapabilityPolicy.allow_all_safe()
        res = self.registry.authorize_and_execute(
            tool_name="large_output",
            arguments={},
            capability_policy=policy,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ToolErrorCode.TOOL_OUTPUT_TOO_LARGE)


if __name__ == "__main__":
    unittest.main()
