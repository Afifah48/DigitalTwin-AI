"""
Anomaly detection schemas and prediction contracts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


def score_to_severity(
    anomaly_score: float,
    low_threshold: float = 0.30,
    high_threshold: float = 0.70,
) -> SeverityLevel:
    """Categorizes raw continuous anomaly score into categorical severity."""
    score = float(anomaly_score)
    if score >= high_threshold:
        return SeverityLevel.HIGH
    elif score >= low_threshold:
        return SeverityLevel.MEDIUM
    else:
        return SeverityLevel.LOW


@dataclass
class AnomalyPrediction:
    """Standardized prediction output payload for station anomaly detection."""
    station_id: str
    timestamp: float
    anomaly_score: float                   # Uncalibrated / model-specific normalized anomaly score [0.0, 1.0]
    anomaly_probability: Optional[float]   # Formally calibrated probability against validation data (or None)
    severity: str                          # LOW, MEDIUM, HIGH
    detected: bool                         # True if score >= anomaly threshold
    lead_time_if_known: Optional[float] = None  # Seconds before bottleneck/failure (when ground truth is known)
    top_signals: List[str] = field(default_factory=list)  # Top contributing feature names to the anomaly
    metadata: Dict[str, Any] = field(default_factory=dict)  # Model version, threshold used, raw scores, etc.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BatchAnomalyPrediction:
    """Aggregated predictions for all stations at a given simulation timestamp."""
    timestamp: float
    predictions: Dict[str, AnomalyPrediction] = field(default_factory=dict)
    anomalous_stations: List[str] = field(default_factory=list)
    highest_anomaly_station: Optional[str] = None
    max_anomaly_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "predictions": {k: v.to_dict() for k, v in self.predictions.items()},
            "anomalous_stations": list(self.anomalous_stations),
            "highest_anomaly_station": self.highest_anomaly_station,
            "max_anomaly_score": round(self.max_anomaly_score, 4),
        }
