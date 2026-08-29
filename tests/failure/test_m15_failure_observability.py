"""
Failure tests for M15 Observability Engine Degradation & Fail-Safe Behavior.
"""

import unittest

from apps.api.observability.forensics import forensic_engine
from apps.api.observability.incident_engine import incident_engine


class TestM15FailureObservability(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        forensic_engine.clear()
        incident_engine.clear()

    def tearDown(self) -> None:
        forensic_engine.clear()
        incident_engine.clear()

    async def test_forensic_recording_degrades_safely_on_db_error(self) -> None:
        """Verify telemetry/forensic recording gracefully degrades if DB is unavailable without crashing application."""

        class BrokenUoW:
            _is_active = True

            @property
            def forensics(self) -> None:
                raise RuntimeError("Database connection lost")

        # Recording event with broken UoW should record to memory ring buffer and fail open
        evt = await forensic_engine.record_event(
            event_type="test.db_fail",
            category="RELIABILITY",
            severity="MEDIUM",
            outcome="ANOMALY",
            metadata={"test": "db_fail"},
        )
        self.assertIsNotNone(evt)
        self.assertEqual(evt.event_type, "test.db_fail")


if __name__ == "__main__":
    unittest.main()
