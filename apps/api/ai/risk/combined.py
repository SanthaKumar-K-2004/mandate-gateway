"""
Combined Risk Intelligence Engine.
Aggregates LLM Signals + ML Risk Model + Neural Anomaly Detector into an explainable policy-input risk score.
"""

from typing import Any, Dict, List, Optional
from apps.api.ai.risk.ml_model import MLRiskClassifier
from apps.api.ai.risk.neural_anomaly import NeuralAnomalyDetector


class CombinedRiskIntelligenceEngine:
    """
    Combined Risk Intelligence Architecture.
    Aggregates multi-model intelligence:
      1. LLM decision risk signals & prompt injection flags
      2. Supervised ML Logistic Risk Classifier
      3. Neural Network Autoencoder Anomaly Detector
    """

    def __init__(self) -> None:
        self.ml_classifier = MLRiskClassifier()
        self.neural_detector = NeuralAnomalyDetector()

    def evaluate_risk(
        self, payload: Dict[str, Any], llm_signals: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Aggregates multi-model risk intelligence and produces a unified explainable risk summary.
        NOTE: Risk scoring is an advisory policy input.
        It NEVER bypasses human confirmation or safety gates.
        """
        llm_signals = llm_signals or {}

        # 1. Evaluate ML model risk score
        ml_result = self.ml_classifier.predict_risk(payload)
        ml_score = ml_result["risk_score"]

        # 2. Evaluate Neural Autoencoder anomaly score
        neural_result = self.neural_detector.detect_anomaly(payload)
        anomaly_score = neural_result["anomaly_score"]

        # 3. Incorporate LLM prompt injection signals
        is_injection = payload.get("prompt_injection_detected", False) or llm_signals.get(
            "prompt_injection_detected", False
        )

        # 4. Compute weighted combined risk score
        if is_injection:
            combined_score = 0.99
            risk_level = "CRITICAL"
        else:
            combined_score = float(0.6 * ml_score + 0.4 * anomaly_score)
            if combined_score >= 0.85:
                risk_level = "CRITICAL"
            elif combined_score >= 0.65:
                risk_level = "HIGH"
            elif combined_score >= 0.35:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

        # Combine all risk factor lists
        combined_factors: List[str] = list(
            set(ml_result["risk_factors"] + neural_result["feature_summary"])
        )
        if is_injection and "PROMPT_INJECTION_DETECTED" not in combined_factors:
            combined_factors.append("PROMPT_INJECTION_DETECTED")

        # Determine required safety action
        if risk_level == "CRITICAL":
            action_recommendation = "BLOCK_AND_FAIL_CLOSED"
        elif risk_level == "HIGH":
            action_recommendation = "REQUIRE_ENHANCED_HUMAN_CONFIRMATION"
        elif risk_level == "MEDIUM":
            action_recommendation = "REQUIRE_HUMAN_CONFIRMATION"
        else:
            action_recommendation = "PROCEED_TO_HUMAN_CONFIRMATION"

        return {
            "combined_risk_score": round(combined_score, 4),
            "risk_level": risk_level,
            "action_recommendation": action_recommendation,
            "ml_risk": ml_result,
            "neural_anomaly": neural_result,
            "risk_factors": combined_factors,
            "prompt_injection_detected": is_injection,
            "requires_human_confirmation": True,  # Non-negotiable invariant
            "explainable_summary": (
                f"Combined Risk: {risk_level} (Score: {combined_score:.2f}). "
                f"ML Risk: {ml_score:.2f}, Neural Anomaly: {anomaly_score:.2f}. "
                f"Action: {action_recommendation}."
            ),
        }
