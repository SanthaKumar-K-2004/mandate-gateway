"""
Unit tests for Pure NumPy Neural Network Autoencoder Anomaly Detector.
"""

import unittest
from apps.api.ai.risk.features import FeatureExtractor
from apps.api.ai.risk.neural_anomaly import NeuralAnomalyDetector


class TestNeuralAnomalyDetector(unittest.TestCase):
    def setUp(self):
        self.extractor = FeatureExtractor()
        self.detector = NeuralAnomalyDetector()

    def test_normal_pattern_low_anomaly_score(self):
        normal_payload = {
            "amount_paise": 20000,
            "budget_paise": 30000,
            "product_verified": True,
            "merchant_risk_score": 0.0,
            "velocity_attempt_count": 1,
            "cart_item_count": 2,
            "prompt_injection_detected": False,
            "human_confirmed": True,
        }
        res = self.detector.detect_anomaly(normal_payload)

        self.assertIn("anomaly_score", res)
        self.assertIn("reconstruction_mse", res)
        self.assertIn("is_anomalous", res)
        self.assertLess(res["anomaly_score"], 0.6)
        self.assertFalse(res["is_anomalous"])

    def test_anomalous_pattern_high_anomaly_score(self):
        # Extreme values out of distribution
        anomalous_payload = {
            "amount_paise": 99999999,
            "budget_paise": 100,
            "product_verified": False,
            "merchant_risk_score": 1.0,
            "velocity_attempt_count": 50,
            "cart_item_count": 100,
            "prompt_injection_detected": True,
            "human_confirmed": False,
        }
        res = self.detector.detect_anomaly(anomalous_payload)

        self.assertGreater(res["anomaly_score"], 0.3)
        self.assertGreater(res["reconstruction_mse"], 0.0)


if __name__ == "__main__":
    unittest.main()
