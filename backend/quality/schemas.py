"""
Vehicle Quality and Defect Prediction Schemas.

Defines the official prediction contracts, data schemas, severity levels,
and operational recommendation actions for Phase 6.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class QualityExposureLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RecommendedAction(str, Enum):
    PASS_MONITOR = "PASS_MONITOR"
    REVIEW_AUDIT = "REVIEW_AUDIT"
    QA_INSPECTION = "QA_INSPECTION"


class DefectSeverity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class TopRiskFactor:
    """Detailed SHAP feature attribution factor."""
    feature: str
    contribution: float
    direction: str  # 'INCREASES_DEFECT_RISK' or 'DECREASES_DEFECT_RISK'
    feature_value: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "feature": self.feature,
            "contribution": round(float(self.contribution), 4),
            "direction": self.direction,
        }
        if self.feature_value is not None:
            res["feature_value"] = round(float(self.feature_value), 4)
        return res


@dataclass
class VehicleRiskPrediction:
    """Official Phase 6 vehicle-level defect prediction contract."""
    vehicle_id: str
    timestamp: float
    risk_score: float                  # Scaled risk score [0.0, 100.0]
    defect_probability: float          # Calibrated probability of defect [0.0, 1.0]
    quality_exposure: str              # 'LOW', 'MEDIUM', 'HIGH'
    recommended_action: str            # 'PASS_MONITOR', 'REVIEW_AUDIT', 'QA_INSPECTION'
    top_risk_factors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Schema validation
        if not isinstance(self.vehicle_id, str) or not self.vehicle_id:
            raise ValueError(f"Invalid vehicle_id: {self.vehicle_id}")
        if not (0.0 <= float(self.defect_probability) <= 1.0):
            raise ValueError(f"defect_probability must be in [0.0, 1.0], got {self.defect_probability}")
        if not (0.0 <= float(self.risk_score) <= 100.0):
            raise ValueError(f"risk_score must be in [0.0, 100.0], got {self.risk_score}")
        if self.quality_exposure not in [e.value for e in QualityExposureLevel]:
            raise ValueError(f"quality_exposure must be LOW, MEDIUM, or HIGH, got {self.quality_exposure}")
        if self.recommended_action not in [a.value for a in RecommendedAction]:
            raise ValueError(f"Invalid recommended_action: {self.recommended_action}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "timestamp": round(float(self.timestamp), 2),
            "risk_score": round(float(self.risk_score), 2),
            "defect_probability": round(float(self.defect_probability), 4),
            "quality_exposure": self.quality_exposure,
            "recommended_action": self.recommended_action,
            "top_risk_factors": self.top_risk_factors,
            "metadata": self.metadata,
        }


@dataclass
class VehicleObservation:
    """A single recorded event/telemetry snapshot of a vehicle at a station."""
    vehicle_id: str
    station_id: str
    timestamp: float
    vehicle_model: str = "Sedan"
    vehicle_variant: str = "Base"
    duration: float = 50.0
    cycle_time: float = 50.0
    cycle_time_delta: float = 0.0
    queue_length: int = 2
    buffer_occupancy: float = 3.0
    temperature: float = 62.0
    vibration: float = 0.09
    motor_current: float = 4.8
    current_variance: float = 0.05
    machine_state: str = "RUNNING"
    torque: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VehicleDefectGroundTruth:
    """Ground-truth defect label for offline training and evaluation."""
    vehicle_id: str
    vehicle_defect: int               # 0 = Normal, 1 = Defective
    defect_type: str = "NONE"          # e.g., 'FASTENER_TORQUE_DEFECT', 'WELD_ALIGNMENT_DEFECT', 'NONE'
    defect_severity: str = "NONE"      # 'NONE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    station_origin: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
