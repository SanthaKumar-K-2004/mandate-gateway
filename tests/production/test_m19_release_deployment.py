"""
M19 Production Deployment Readiness Suite
==========================================
Workstream F — Verifies production deployment documentation, release checklists,
environment variable templates, and migration procedures.
"""

from __future__ import annotations

import unittest
from pathlib import Path


class TestM19ReleaseDeployment(unittest.TestCase):
    """Release deployment certification suite."""

    def setUp(self) -> None:
        self.root_dir = Path(__file__).resolve().parents[2]

    def test_01_deployment_guide_exists_and_contains_sections(self) -> None:
        """Verify DEPLOYMENT_GUIDE_M19.md exists and contains deployment sections."""
        guide_path = self.root_dir / "docs" / "deployment" / "DEPLOYMENT_GUIDE_M19.md"
        self.assertTrue(
            guide_path.exists(), "DEPLOYMENT_GUIDE_M19.md must exist in docs/deployment/"
        )

        content = guide_path.read_text(encoding="utf-8")
        self.assertIn("Environment Variable Template", content)
        self.assertIn("Database Migration Strategy", content)
        self.assertIn("Rollback Procedure", content)
        self.assertIn("Production Health Check Probes", content)
        self.assertIn("Production Release Verification Checklist", content)

    def test_02_environment_template_keys(self) -> None:
        """Verify environment variable template defines required parameters."""
        guide_path = self.root_dir / "docs" / "deployment" / "DEPLOYMENT_GUIDE_M19.md"
        content = guide_path.read_text(encoding="utf-8")

        required_keys = [
            "APP_ENV=",
            "POSTGRES_HOST=",
            "POSTGRES_PASSWORD=",
            "REDIS_HOST=",
            "OPERATOR_SECRET_TOKEN=",
        ]
        for key in required_keys:
            self.assertIn(key, content, f"Deployment template missing required key: {key}")


if __name__ == "__main__":
    unittest.main()
