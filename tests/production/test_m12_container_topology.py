"""
M12 Container Topology & Runtime Security Certification Suite
=============================================================
Verifies Dockerfile multi-stage build structure, non-root user execution,
docker-compose.yml service topology, and production configuration safety.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from apps.api.config.settings import Settings


class TestM12ContainerTopology(unittest.TestCase):
    """Container topology and runtime security certification tests."""

    def setUp(self) -> None:
        """Set root directory path."""
        self.root_dir = Path(__file__).resolve().parents[2]

    def test_01_dockerfile_multi_stage_and_non_root_user(self) -> None:
        """Verify Dockerfile uses multi-stage builds and runs as appuser:appgroup."""
        dockerfile_path = self.root_dir / "Dockerfile"
        self.assertTrue(dockerfile_path.exists(), "Dockerfile must exist at repository root")

        content = dockerfile_path.read_text(encoding="utf-8")
        self.assertIn("FROM python:", content, "Dockerfile must build from Python base image")
        self.assertIn("AS builder", content, "Dockerfile must include builder stage")
        self.assertIn(
            "USER appuser:appgroup",
            content,
            "Dockerfile must specify non-root USER appuser:appgroup",
        )

    def test_02_docker_ignore_secret_exclusion(self) -> None:
        """Verify .dockerignore excludes sensitive files."""
        ignore_path = self.root_dir / ".dockerignore"
        self.assertTrue(ignore_path.exists(), ".dockerignore must exist at repository root")

        content = ignore_path.read_text(encoding="utf-8")
        excluded_items = [".env", ".git", "__pycache__", "tests"]
        for item in excluded_items:
            self.assertIn(item, content, f".dockerignore must exclude '{item}'")

    def test_03_docker_compose_topology_validation(self) -> None:
        """Verify docker-compose.yml specifies required services and health checks."""
        compose_path = self.root_dir / "docker-compose.yml"
        self.assertTrue(compose_path.exists(), "docker-compose.yml must exist at repository root")

        content = compose_path.read_text(encoding="utf-8")
        expected_services = ["postgres:", "redis:", "api:", "outbox_worker:", "recovery_worker:"]
        for svc in expected_services:
            self.assertIn(svc, content, f"docker-compose.yml must include service '{svc}'")

        self.assertIn("healthcheck:", content, "docker-compose.yml must define healthcheck")

    def test_04_fail_fast_production_configuration_validation(self) -> None:
        """Verify validate_production_config rejects unsafe credentials in production mode."""
        with self.assertRaises((ValueError, Exception)) as cm:
            Settings.from_env(
                env_dict={
                    "APP_ENV": "production",
                    "POSTGRES_PASSWORD": "postgres",
                    "REDIS_HOST": "redis",
                }
            )
        self.assertTrue(
            "POSTGRES_PASSWORD" in str(cm.exception) or "production" in str(cm.exception)
        )


if __name__ == "__main__":
    unittest.main()
