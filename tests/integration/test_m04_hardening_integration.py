"""
M04 — System Hardening Integration Test Suite.
"""

import unittest

from apps.api.app.factory import create_fastapi_app


class TestM04HardeningIntegration(unittest.TestCase):
    """Integration test suite for M04 hardening REST API router endpoints."""

    def setUp(self) -> None:
        self.app = create_fastapi_app()

    def test_app_router_registration(self) -> None:
        self.assertIsNotNone(self.app)
        routes = [r.path for r in self.app.routes]
        self.assertIn("/api/hardening/audit", routes)
        self.assertIn("/api/hardening/concurrency-stress", routes)
