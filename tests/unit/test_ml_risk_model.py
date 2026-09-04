"""
Unit tests for Pure NumPy ML Risk Classifier Model.
"""

import unittest
import numpy as np
from apps.api.ai.risk.features import FeatureExtractor
from apps.api.ai.risk.ml_model import MLRiskClassifier


class TestMLRiskModel(unittest.TestCase):
    def setUp(self):
        self.extractor = FeatureExtractor()
        self.classifier = MLRiskClassifier()

    def test_feature_extractor_normalization(self):
        payload = {
            "amount_paise": 150000,
            "budget_paise": 100000,
            "product_verified": True,
            "merchant_risk_score": 0.2,
            "velocity_attempt_count": 2,
            "cart_item_count": 3,
            "prompt_injection_detected": False,
            "human_confirmed": True,
        }
        vec = self.extractor.extract_features(payload)
        self.assertEqual(len(vec), 10)
        # Verify vector values are normalized floats
        for val in vec:
            self.assertTrue(isinstance(val, (float, int, np.floating)))

    def test_ml_classifier_low_risk(self):
        payload = {
            "amount_paise": 25000,
            "budget_paise": 30000,
            "product_verified": True,
            "merchant_risk_score": 0.05,
            "velocity_attempt_count": 1,
            "cart_item_count": 2,
            "prompt_injection_detected": False,
            "human_confirmed": True,
        }
        res = self.classifier.predict_risk(payload)

        self.assertIn("risk_score", res)
        self.assertIn("risk_level", res)
        self.assertIn("model_version", res)
        self.assertLess(res["risk_score"], 0.4)
        self.assertEqual(res["risk_level"], "LOW")

    def test_ml_classifier_high_risk_prompt_injection(self):
        payload = {
            "amount_paise": 250000,
            "budget_paise": 30000,
            "product_verified": False,
            "merchant_risk_score": 0.9,
            "velocity_attempt_count": 10,
            "cart_item_count": 1,
            "prompt_injection_detected": True,
            "human_confirmed": False,
        }
        res = self.classifier.predict_risk(payload)

        self.assertGreaterEqual(res["risk_score"], 0.5)
        self.assertIn(res["risk_level"], ["HIGH", "CRITICAL"])


if __name__ == "__main__":
    unittest.main()
