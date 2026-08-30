"""
M21 Container Hardening & Topology Static Verification Suite
============================================================
Workstream 3 & 4 — Performs static validation of Dockerfile, docker-compose.yml,
and docker-compose.prod.yml to verify container security, non-root execution,
healthchecks, and independent worker process separation.
"""

from __future__ import annotations

import os
import unittest


class TestM21ContainerHardening(unittest.TestCase):
    """Container hardening and topology verification suite."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.dockerfile_path = os.path.join(self.root_dir, "Dockerfile")
        self.compose_path = os.path.join(self.root_dir, "docker-compose.yml")
        self.compose_prod_path = os.path.join(self.root_dir, "docker-compose.prod.yml")

    def test_01_dockerfile_multi_stage_and_non_root(self) -> None:
        """Verify Dockerfile uses multi-stage build, non-root execution, and healthcheck."""
        self.assertTrue(os.path.exists(self.dockerfile_path), "Dockerfile missing")
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("AS builder", content)
        self.assertIn("AS runtime", content)
        self.assertIn("USER appuser", content)
        self.assertIn("HEALTHCHECK", content)
        self.assertNotIn("BEGIN PRIVATE KEY", content)

    def test_02_production_compose_topology(self) -> None:
        """Verify docker-compose.prod.yml defines API, outbox worker, recovery worker, DB, and Redis."""
        self.assertTrue(os.path.exists(self.compose_prod_path), "docker-compose.prod.yml missing")
        with open(self.compose_prod_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("postgres:", content)
        self.assertIn("redis:", content)
        self.assertIn("api:", content)
        self.assertIn("outbox_worker:", content)
        self.assertIn("recovery_worker:", content)
        self.assertIn("postgres_prod_data:", content)
        self.assertIn("redis_prod_data:", content)

    def test_03_zero_baked_secrets_in_compose(self) -> None:
        """Verify container compose configurations bake zero production secrets."""
        for path in (self.compose_path, self.compose_prod_path):
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertNotIn("AWS_SECRET_ACCESS_KEY=", content)
                self.assertNotIn("PRIVATE_KEY=", content)


if __name__ == "__main__":
    unittest.main()
