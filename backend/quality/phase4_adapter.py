"""
Phase 4 Anomaly Detection Adapter for Phase 6 Quality Prediction.

Provides clean, time-aware access to Phase 4 anomaly detection outputs
without duplicating internal model logic or leaking future information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union

from backend.app.schemas.anomaly import AnomalyPrediction, BatchAnomalyPrediction


@dataclass
class StationAnomalySummary:
    """Consolidated Phase 4 anomaly exposure metrics for a station up to a timestamp."""
    station_id: str
    as_of_timestamp: float
    mean_anomaly_score: float = 0.0
    max_anomaly_score: float = 0.0
    latest_anomaly_score: float = 0.0
    anomaly_detected_count: int = 0
    is_currently_anomalous: bool = False
    severity_level: str = "LOW"
    top_signals: List[str] = field(default_factory=list)


class Phase4Adapter:
    """
    Time-aware adapter consuming Phase 4 Anomaly Detection outputs.

    Ensures that when queried for information at timestamp `t`, only anomaly
    predictions generated at or before `t` (timestamp <= as_of_timestamp) are returned.
    """

    def __init__(self, historical_predictions: Optional[Sequence[Union[AnomalyPrediction, Dict[str, Any]]]] = None) -> None:
        self._predictions: List[AnomalyPrediction] = []
        if historical_predictions:
            self.ingest_predictions(historical_predictions)

    def ingest_prediction(self, prediction: Union[AnomalyPrediction, Dict[str, Any]]) -> None:
        """Adds a single Phase 4 prediction to the historical registry."""
        if isinstance(prediction, dict):
            p = AnomalyPrediction(
                station_id=str(prediction.get("station_id", "")),
                timestamp=float(prediction.get("timestamp", 0.0)),
                anomaly_score=float(prediction.get("anomaly_score", 0.0)),
                anomaly_probability=prediction.get("anomaly_probability"),
                severity=str(prediction.get("severity", "LOW")),
                detected=bool(prediction.get("detected", False)),
                lead_time_if_known=prediction.get("lead_time_if_known"),
                top_signals=list(prediction.get("top_signals", [])),
                metadata=dict(prediction.get("metadata", {})),
            )
        elif isinstance(prediction, AnomalyPrediction):
            p = prediction
        else:
            raise TypeError(f"Expected AnomalyPrediction or dict, got {type(prediction)}")
        self._predictions.append(p)

    def ingest_predictions(self, predictions: Sequence[Union[AnomalyPrediction, Dict[str, Any]]]) -> None:
        """Batch ingests multiple Phase 4 predictions."""
        for p in predictions:
            self.ingest_prediction(p)

    def ingest_batch_prediction(self, batch: BatchAnomalyPrediction) -> None:
        """Ingests a BatchAnomalyPrediction snapshot."""
        for _, p in batch.predictions.items():
            self.ingest_prediction(p)

    def get_predictions_as_of(
        self,
        as_of_timestamp: float,
        station_id: Optional[str] = None,
    ) -> List[AnomalyPrediction]:
        """
        Retrieves Phase 4 predictions strictly on or before `as_of_timestamp`.
        Future predictions (timestamp > as_of_timestamp) are excluded.
        """
        valid = [
            p for p in self._predictions
            if p.timestamp <= as_of_timestamp and (station_id is None or p.station_id == station_id)
        ]
        return sorted(valid, key=lambda x: x.timestamp)

    def get_station_summary(
        self,
        station_id: str,
        as_of_timestamp: float,
    ) -> StationAnomalySummary:
        """
        Aggregates time-bounded anomaly exposure for a specific station up to `as_of_timestamp`.
        """
        station_preds = self.get_predictions_as_of(as_of_timestamp=as_of_timestamp, station_id=station_id)
        if not station_preds:
            return StationAnomalySummary(station_id=station_id, as_of_timestamp=as_of_timestamp)

        scores = [p.anomaly_score for p in station_preds]
        detected_flags = [p.detected for p in station_preds]
        latest_p = station_preds[-1]

        # Aggregate unique top signals
        signal_counts: Dict[str, int] = {}
        for p in station_preds:
            for sig in p.top_signals:
                signal_counts[sig] = signal_counts.get(sig, 0) + 1
        sorted_signals = sorted(signal_counts.keys(), key=lambda s: signal_counts[s], reverse=True)

        return StationAnomalySummary(
            station_id=station_id,
            as_of_timestamp=as_of_timestamp,
            mean_anomaly_score=float(sum(scores) / len(scores)),
            max_anomaly_score=float(max(scores)),
            latest_anomaly_score=float(latest_p.anomaly_score),
            anomaly_detected_count=int(sum(1 for d in detected_flags if d)),
            is_currently_anomalous=bool(latest_p.detected),
            severity_level=str(latest_p.severity),
            top_signals=sorted_signals[:3],
        )
