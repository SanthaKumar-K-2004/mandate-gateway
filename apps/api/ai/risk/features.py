"""
Risk Feature Extractor.
Extracts normalized numerical feature vectors from transaction and context payloads for ML and Neural models.
"""

from typing import Any
import numpy as np


class FeatureExtractor:
    """Extracts a 10-dimensional normalized numeric feature vector for risk models."""

    FEATURE_NAMES = [
        "normalized_amount",  # 0: amount_paise / 100000 (cap at 1.0)
        "amount_budget_ratio",  # 1: amount / budget (0.0 to 1.0+)
        "unverified_product_flag",  # 2: 1.0 if any product unverified, else 0.0
        "merchant_risk_score",  # 3: 0.0 (trusted) to 1.0 (unknown/high risk)
        "velocity_attempt_count",  # 4: attempts in window / 10
        "confirmation_timing_sec",  # 5: time since confirmation / 60
        "cart_item_count",  # 6: items / 10
        "prompt_injection_flag",  # 7: 1.0 if injection signal, else 0.0
        "protocol_risk_weight",  # 8: 0.1 for Razorpay test, 0.3 for x402, 0.2 for UAP
        "retry_failure_count",  # 9: previous failed retries / 5
    ]

    def extract_features(self, payload: Any) -> np.ndarray:
        """
        Extracts a normalized NumPy 1D vector of shape (10,).
        Accepts dict payload, list, or existing np.ndarray.
        """
        if isinstance(payload, np.ndarray):
            return payload.astype(np.float32)
        if isinstance(payload, list):
            return np.array(payload, dtype=np.float32)

        amount_paise = float(payload.get("amount_paise", 0))
        budget_paise = float(payload.get("budget_paise", 50000))
        if budget_paise <= 0:
            budget_paise = 50000.0

        normalized_amount = min(amount_paise / 100000.0, 1.0)
        amount_budget_ratio = min(amount_paise / budget_paise, 2.0)
        unverified_flag = 1.0 if not payload.get("product_verified", True) else 0.0
        merchant_risk = float(payload.get("merchant_risk_score", 0.1))
        velocity = float(payload.get("velocity_attempt_count", 1)) / 10.0
        timing = float(payload.get("confirmation_timing_sec", 5.0)) / 60.0
        item_count = float(payload.get("cart_item_count", 2)) / 10.0
        injection_flag = 1.0 if payload.get("prompt_injection_detected", False) else 0.0

        protocol = payload.get("payment_protocol", "razorpay").lower()
        protocol_weight = 0.1 if "razorpay" in protocol else (0.3 if "x402" in protocol else 0.2)
        retry_count = float(payload.get("retry_failure_count", 0)) / 5.0

        features = [
            normalized_amount,
            amount_budget_ratio,
            unverified_flag,
            merchant_risk,
            velocity,
            timing,
            item_count,
            injection_flag,
            protocol_weight,
            retry_count,
        ]

        return np.array(features, dtype=np.float32)
