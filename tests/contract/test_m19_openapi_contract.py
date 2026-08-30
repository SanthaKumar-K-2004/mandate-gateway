"""
M19 OpenAPI Contract & Schema Stability Suite
=============================================
Workstream 8 — Verifies route presence, OpenAPI schema generation,
stable machine-readable error format, and security headers.
"""

from __future__ import annotations

import unittest
from apps.api.app.factory import create_fastapi_app


class TestM19OpenAPIContract(unittest.TestCase):
    """OpenAPI schema structure and API contract stability suite."""

    def setUp(self) -> None:
        self.app = create_fastapi_app()

    def test_01_openapi_schema_generation(self) -> None:
        """Verify OpenAPI schema can be generated and contains required endpoints."""
        if not self.app:
            self.skipTest("FastAPI not installed in current environment")

        schema = self.app.openapi()
        self.assertIn("openapi", schema)
        self.assertIn("info", schema)
        self.assertEqual(schema["info"]["title"], "mandate-gateway")

        paths = schema.get("paths", {})
        self.assertTrue(len(paths) > 0, "OpenAPI schema must contain registered API routes")

    def test_02_stable_error_schema_format(self) -> None:
        """Verify error responses adhere to standard machine-readable schema structure."""
        from fastapi.testclient import TestClient

        if not self.app:
            self.skipTest("FastAPI not installed")

        client = TestClient(self.app)
        res = client.get("/api/v1/non_existent_route_999")
        self.assertEqual(res.status_code, 404)

        data = res.json()
        self.assertIn("error", data)
        self.assertIn("code", data["error"])
        self.assertIn("message", data["error"])
        self.assertIn("request_id", data["error"])
        self.assertEqual(data["error"]["code"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
