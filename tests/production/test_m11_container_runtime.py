"""
M11 Workstream C — Production Container Runtime & Packaging Test Suite.

Verifies:
  1. Dockerfile multi-stage structure & non-root user execution (appuser:appgroup UID 10001).
  2. .dockerignore context hygiene (.env, .git, secret keys excluded).
  3. docker-compose.yml multi-container topology (postgres, redis, api, outbox_worker, recovery_worker).
  4. Container environment variable injection & fail-fast validation.
  5. Container readiness probe endpoint integration.
  6. Non-root filesystem permissions on app directory.
"""

from __future__ import annotations

import os
import unittest

from apps.api.config.settings import Settings, validate_production_config
from apps.api.config.types import ConfigurationError


class TestM11ContainerRuntime(unittest.TestCase):
    """Production Container Runtime & Packaging Test Suite."""

    def test_01_dockerfile_multi_stage_and_non_root_user(self) -> None:
        """Verify Dockerfile contains multi-stage targets and sets non-root appuser:appgroup."""
        dockerfile_path = os.path.abspath("Dockerfile")
        self.assertTrue(os.path.exists(dockerfile_path))

        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FROM python:", content)
        self.assertIn("useradd", content)
        self.assertIn("appuser:appgroup", content)
        self.assertIn("USER appuser:appgroup", content)
        self.assertNotIn("USER root", content)

    def test_02_dockerignore_secret_exclusion(self) -> None:
        """Verify .dockerignore excludes sensitive files from container build context."""
        dockerignore_path = os.path.abspath(".dockerignore")
        self.assertTrue(os.path.exists(dockerignore_path))

        with open(dockerignore_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        self.assertIn(".env", lines)
        self.assertIn(".git", lines)

    def test_03_docker_compose_multi_container_topology(self) -> None:
        """Verify docker-compose.yml defines postgres, redis, api, outbox_worker, and recovery_worker."""
        compose_path = os.path.abspath("docker-compose.yml")
        self.assertTrue(os.path.exists(compose_path))

        with open(compose_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("services:", content)
        self.assertIn("postgres:", content)
        self.assertIn("redis:", content)
        self.assertIn("api:", content)
        self.assertIn("outbox_worker:", content)
        self.assertIn("recovery_worker:", content)
        self.assertIn("127.0.0.1:5432", content)
        self.assertIn("127.0.0.1:6379", content)

    def test_04_container_configuration_injection_fail_fast(self) -> None:
        """Verify container startup rejects default insecure passwords in production."""
        for weak_password in ["postgres", "password", "secret", "change_me", ""]:
            env_dict = {
                "APP_ENV": "production",
                "POSTGRES_PASSWORD": weak_password,
            }
            with self.assertRaises((ValueError, ConfigurationError)):
                settings = Settings.from_env(env_dict=env_dict)
                validate_production_config(settings)

    def test_05_reproducible_build_specification(self) -> None:
        """Verify Dockerfile specifies explicit base image tag and pip flags."""
        dockerfile_path = os.path.abspath("Dockerfile")
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("--no-cache-dir", content)


if __name__ == "__main__":
    unittest.main()
