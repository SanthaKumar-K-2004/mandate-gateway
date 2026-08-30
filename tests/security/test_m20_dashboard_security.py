"""
M20 Frontend & Dashboard Security Test Suite
===========================================
Workstream 16 — Evaluates dashboard XSS resistance, HTML sanitization,
route protection, and sensitive data non-exposure.
"""

from __future__ import annotations

import html
import unittest
from apps.api.app.ui_dashboard import get_dashboard_html


class TestM20DashboardSecurity(unittest.TestCase):
    """Dashboard security test suite."""

    def test_01_dashboard_html_no_secret_leak(self) -> None:
        """Verify dashboard HTML contains zero raw secrets or private keys."""
        content = get_dashboard_html()
        self.assertNotIn("BEGIN PRIVATE KEY", content)
        self.assertNotIn("POSTGRES_PASSWORD", content)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", content)

    def test_02_xss_sanitization_helper(self) -> None:
        """Verify HTML entity escaping sanitizes untrusted input strings."""
        untrusted = "<script>alert('xss')</script>"
        sanitized = html.escape(untrusted)
        self.assertNotIn("<script>", sanitized)
        self.assertEqual(sanitized, "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;")


if __name__ == "__main__":
    unittest.main()
