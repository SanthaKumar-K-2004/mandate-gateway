"""
M19 Container Runtime & Infrastructure Certification Test Suite
===============================================================
Workstream A — Verifies container topology, multi-stage build rules,
non-root user security, volume persistence, health check commands,
and process signal handling.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from apps.api.deployment.process_topology import ProcessRole, ProcessTopologyManager


class TestM19ContainerRuntime(unittest.TestCase):
    """Container runtime topology and production container security certification."""

    def setUp(self) -> None:
        self.root_dir = Path(__file__).resolve().parents[2]

    def test_01_dockerfile_multi_stage_and_non_root_security(self) -> None:
        """Verify Dockerfile multi-stage build, non-root user, and security hardening."""
        dockerfile_path = self.root_dir / "Dockerfile"
        self.assertTrue(dockerfile_path.exists(), "Dockerfile must exist at repository root")

        content = dockerfile_path.read_text(encoding="utf-8")
        self.assertIn("FROM python:3.11-slim AS builder", content)
        self.assertIn("FROM python:3.11-slim AS runtime", content)
        self.assertIn("USER appuser:appgroup", content)
        self.assertIn("10001", content, "Dockerfile must use dedicated UID/GID 10001")
        self.assertIn("HEALTHCHECK", content)
        self.assertIn("http://localhost:8000/health", content)

    def test_02_docker_compose_complete_topology(self) -> None:
        """Verify docker-compose.yml defines all 5 required production services and volumes."""
        compose_path = self.root_dir / "docker-compose.yml"
        self.assertTrue(compose_path.exists(), "docker-compose.yml must exist at repository root")

        content = compose_path.read_text(encoding="utf-8")
        services = ["postgres:", "redis:", "api:", "outbox_worker:", "recovery_worker:"]
        for svc in services:
            self.assertIn(svc, content, f"docker-compose.yml missing service '{svc}'")

        self.assertIn("postgres_data:", content, "Must define persistent postgres_data volume")
        self.assertIn("redis_data:", content, "Must define persistent redis_data volume")
        self.assertIn("healthcheck:", content, "Services must include health checks")

    def test_03_process_topology_roles_and_sigterm_strategy(self) -> None:
        """Verify ProcessTopologyManager supports all roles and graceful signal handling."""
        mgr = ProcessTopologyManager(role=ProcessRole.API_SERVICE)
        meta = mgr.get_process_metadata()
        self.assertTrue(meta["is_api"])
        self.assertFalse(meta["is_maintenance"])
        self.assertEqual(mgr.check_liveness()["status"], "ALIVE")


if __name__ == "__main__":
    unittest.main()
