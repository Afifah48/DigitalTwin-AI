"""
Phase 4 Anomaly Adapter for Phase 7 Decision Layer.

Provides clean, strictly time-bounded access to Phase 4 anomaly detection outputs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from backend.app.schemas.anomaly import AnomalyPrediction, BatchAnomalyPrediction


class Phase4DecisionAdapter:
    """
    Time-bounded adapter for Phase 4 anomaly detection results.
    """

    def __init__(self, historical_predictions: Optional[Sequence[Union[AnomalyPrediction, Dict[str, Any]]]] = None) -> None:
        self._predictions: List[AnomalyPrediction] = []
        if historical_predictions:
            self.ingest_predictions(historical_predictions)

    def ingest_prediction(self, prediction: Union[AnomalyPrediction, Dict[str, Any]]) -> None:
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
        for p in predictions:
            self.ingest_prediction(p)

    def ingest_batch_prediction(self, batch: BatchAnomalyPrediction) -> None:
        for _, p in batch.predictions.items():
            self.ingest_prediction(p)

    def get_predictions_as_of(
        self,
        as_of_timestamp: float,
        station_id: Optional[str] = None,
    ) -> List[AnomalyPrediction]:
        """Strictly returns predictions on or before `as_of_timestamp`."""
        valid = [
            p for p in self._predictions
            if p.timestamp <= as_of_timestamp and (station_id is None or p.station_id == station_id)
        ]
        return sorted(valid, key=lambda x: x.timestamp)

    def get_latest_station_predictions(
        self,
        as_of_timestamp: float,
    ) -> Dict[str, AnomalyPrediction]:
        """Returns the most recent prediction for each station strictly on or before `as_of_timestamp`."""
        valid = self.get_predictions_as_of(as_of_timestamp)
        latest_map: Dict[str, AnomalyPrediction] = {}
        for p in valid:
            latest_map[p.station_id] = p
        return latest_map

    def get_anomalous_stations(
        self,
        as_of_timestamp: float,
    ) -> List[str]:
        """Returns station IDs currently flagged with active anomalies."""
        latest = self.get_latest_station_predictions(as_of_timestamp)
        return sorted([st_id for st_id, p in latest.items() if p.detected])
