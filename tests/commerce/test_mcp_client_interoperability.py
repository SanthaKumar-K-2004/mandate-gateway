"""
Unit tests for External MCP Client Interoperability (M26).
"""

from __future__ import annotations

import unittest

from scripts.mcp_client_test_runner import run_mcp_client_interoperability_suite


class TestMCPClientInteroperability(unittest.TestCase):
    """MCP Client Interoperability test suite."""

    def test_01_run_mcp_client_suite(self) -> None:
        """Verify external MCP client interoperability suite completes cleanly."""
        res = run_mcp_client_interoperability_suite()
        self.assertEqual(res, 0)
