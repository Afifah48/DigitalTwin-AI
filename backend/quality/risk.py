"""
Risk Scoring and Operational Recommendation Policy Module.

Transforms calibrated defect probabilities into continuous risk scores,
categorical quality exposure tiers, and actionable plant floor decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from backend.quality.schemas import QualityExposureLevel, RecommendedAction


@dataclass
class QualityRiskPolicy:
    """
    Operational thresholds and action routing policy.

    Rationale:
    - low_threshold (0.25): Vehicles with <25% risk are considered within normal statistical variance.
    - high_threshold (0.60): Vehicles with >=60% probability of defect represent substantial containment risk.
    """
    low_threshold: float = 0.25
    high_threshold: float = 0.60

    def evaluate_risk(self, defect_probability: float) -> Tuple[float, str, str]:
        """
        Maps continuous defect probability to:
        1. risk_score (0.0 - 100.0)
        2. quality_exposure (LOW, MEDIUM, HIGH)
        3. recommended_action (PASS_MONITOR, REVIEW_AUDIT, QA_INSPECTION)
        """
        prob = float(min(1.0, max(0.0, defect_probability)))
        risk_score = round(prob * 100.0, 2)

        if prob >= self.high_threshold:
            exposure = QualityExposureLevel.HIGH.value
            action = RecommendedAction.QA_INSPECTION.value
        elif prob >= self.low_threshold:
            exposure = QualityExposureLevel.MEDIUM.value
            action = RecommendedAction.REVIEW_AUDIT.value
        else:
            exposure = QualityExposureLevel.LOW.value
            action = RecommendedAction.PASS_MONITOR.value

        return risk_score, exposure, action


DEFAULT_RISK_POLICY = QualityRiskPolicy()


def compute_vehicle_risk(
    defect_probability: float,
    policy: QualityRiskPolicy = DEFAULT_RISK_POLICY,
) -> Tuple[float, str, str]:
    """Convenience function evaluating defect probability against the default operational policy."""
    return policy.evaluate_risk(defect_probability)
