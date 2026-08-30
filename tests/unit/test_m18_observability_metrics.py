"""
Mandate Gateway — Milestone M18 Unit Tests
Workstream B & C — Observability, Metrics & Secret Redaction
"""

import unittest
from apps.api.app.metrics import MetricsRegistry
from apps.api.app.logging import SecretString, redact_sensitive_data


class TestM18ObservabilityMetrics(unittest.TestCase):

    def setUp(self) -> None:
        self.metrics = MetricsRegistry()

    def test_metrics_counters_and_gauges(self) -> None:
        self.metrics.increment_counter(
            "payment_requests_total", value=1, labels={"environment": "production"}
        )
        val = self.metrics.get_counter_value(
            "payment_requests_total", labels={"environment": "production"}
        )
        self.assertEqual(val, 1)

        self.metrics.set_gauge("outbox_backlog_count", value=5.0)
        gauge_val = self.metrics.get_gauge_value("outbox_backlog_count")
        self.assertEqual(gauge_val, 5.0)

    def test_invalid_label_rejection(self) -> None:
        with self.assertRaises(ValueError):
            self.metrics.increment_counter(
                "payment_requests_total", labels={"unauthorized_cardinality_key": "bad"}
            )

    def test_prometheus_text_format(self) -> None:
        self.metrics.increment_counter("payment_success_total")
        text = self.metrics.to_prometheus_text()
        self.assertIn("payment_success_total", text)
        self.assertIn("TYPE payment_success_total counter", text)

    def test_secret_string_redaction(self) -> None:
        sec = SecretString("super_secret_api_key_123")
        self.assertEqual(str(sec), "[REDACTED]")
        self.assertIn("[REDACTED]", repr(sec))
        self.assertEqual(sec.get_secret_value(), "super_secret_api_key_123")

    def test_dictionary_redaction(self) -> None:
        payload = {
            "merchant_id": "mer_123",
            "password": "my_secret_pass",
            "api_key": "rzp_live_secret",
            "amount_paise": 5000,
        }
        redacted = redact_sensitive_data(payload)
        self.assertEqual(redacted["merchant_id"], "mer_123")
        self.assertEqual(redacted["password"], "[REDACTED]")
        self.assertEqual(redacted["api_key"], "[REDACTED]")
        self.assertEqual(redacted["amount_paise"], 5000)


if __name__ == "__main__":
    unittest.main()
