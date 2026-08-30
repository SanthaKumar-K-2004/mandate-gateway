"""
Unit tests for M17 Release Artifact Integrity & Recovery Components.
"""

import unittest
from apps.api.deployment.release_manifest import (
    ReleaseManifest,
    generate_release_manifest,
    verify_release_manifest,
)
from apps.api.observability.recovery_tracker import recovery_tracker


class TestM17ReleaseCertificationUnit(unittest.TestCase):
    def test_generate_and_verify_release_manifest(self) -> None:
        """Verify release manifest generation and checksum validation."""
        manifest = generate_release_manifest(environment="test")
        self.assertEqual(manifest.environment, "test")
        self.assertIsNotNone(manifest.git_commit_sha)

        res = verify_release_manifest(manifest)
        self.assertTrue(res["valid"])

    def test_tampered_release_manifest_rejected(self) -> None:
        """Verify manifest verification fails closed when artifact checksum is tampered."""
        manifest = ReleaseManifest(
            git_commit_sha="invalid_sha",
            app_version="1.0.0",
            schema_revision="001_initial_schema",
            pyproject_hash="1111111111111111111111111111111111111111111111111111111111111111",
            artifact_checksum="bad_checksum_hash",
            release_timestamp="2026-08-30T12:00:00Z",
            environment="production",
        )
        with self.assertRaises(ValueError):
            verify_release_manifest(manifest)

    def test_recovery_tracker_timing_measurement(self) -> None:
        """Verify recovery tracker records start, end, and duration accurately."""
        record = recovery_tracker.start_recovery_session("rec_sess_001", "simulated")
        self.assertEqual(record.session_id, "rec_sess_001")

        summary = recovery_tracker.complete_recovery_session(
            session_id="rec_sess_001",
            reconciled_count=5,
            unknown_count=1,
            outbox_count=10,
            audit_passed=True,
            receipt_passed=True,
        )
        self.assertGreaterEqual(summary["duration_seconds"], 0.0)
        self.assertTrue(summary["audit_verification_passed"])
        self.assertEqual(summary["transactions_reconciled"], 5)


if __name__ == "__main__":
    unittest.main()
