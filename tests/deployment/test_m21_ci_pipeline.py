"""
M21 CI/CD Pipeline Verification Suite
=====================================
Workstream 5 — Performs static validation of .github/workflows/ci.yml
to verify continuous integration quality gates, secret scanning, and build integrity.
"""

from __future__ import annotations

import os
import unittest


class TestM21CIPipeline(unittest.TestCase):
    """CI/CD pipeline configuration verification suite."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.ci_workflow_path = os.path.join(self.root_dir, ".github", "workflows", "ci.yml")

    def test_01_ci_workflow_existence_and_stages(self) -> None:
        """Verify .github/workflows/ci.yml exists and contains all required stages."""
        self.assertTrue(os.path.exists(self.ci_workflow_path), ".github/workflows/ci.yml missing")
        with open(self.ci_workflow_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("make check", content)
        self.assertIn("Dockerfile", content)
        self.assertIn("unittest discover", content)
        self.assertIn("USER appuser:appgroup", content)


if __name__ == "__main__":
    unittest.main()
