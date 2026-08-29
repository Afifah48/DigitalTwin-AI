"""
Phase 6 Vehicle Quality Adapter for Phase 7 Decision Layer.

Provides clean, time-bounded access to Phase 6 vehicle quality predictions,
defect risk scores, and top SHAP risk factors.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from backend.quality.schemas import VehicleRiskPrediction


class Phase6DecisionAdapter:
    """
    Time-bounded adapter consuming Phase 6 Vehicle Risk predictions.
    """

    def __init__(self, historical_predictions: Optional[Sequence[Union[VehicleRiskPrediction, Dict[str, Any]]]] = None) -> None:
        self._predictions: List[VehicleRiskPrediction] = []
        if historical_predictions:
            self.ingest_predictions(historical_predictions)

    def ingest_prediction(self, prediction: Union[VehicleRiskPrediction, Dict[str, Any]]) -> None:
        if isinstance(prediction, dict):
            p = VehicleRiskPrediction(
                vehicle_id=str(prediction.get("vehicle_id", "")),
                timestamp=float(prediction.get("timestamp", 0.0)),
                risk_score=float(prediction.get("risk_score", 0.0)),
                defect_probability=float(prediction.get("defect_probability", 0.0)),
                quality_exposure=str(prediction.get("quality_exposure", "LOW")),
                recommended_action=str(prediction.get("recommended_action", "PASS_MONITOR")),
                top_risk_factors=list(prediction.get("top_risk_factors", [])),
                metadata=dict(prediction.get("metadata", {})),
            )
        elif isinstance(prediction, VehicleRiskPrediction):
            p = prediction
        else:
            raise TypeError(f"Expected VehicleRiskPrediction or dict, got {type(prediction)}")

        self._predictions.append(p)

    def ingest_predictions(self, predictions: Sequence[Union[VehicleRiskPrediction, Dict[str, Any]]]) -> None:
        for p in predictions:
            self.ingest_prediction(p)

    def get_predictions_as_of(
        self,
        as_of_timestamp: float,
        vehicle_id: Optional[str] = None,
    ) -> List[VehicleRiskPrediction]:
        """Strictly returns vehicle risk predictions on or before `as_of_timestamp`."""
        valid = [
            p for p in self._predictions
            if p.timestamp <= as_of_timestamp and (vehicle_id is None or p.vehicle_id == vehicle_id)
        ]
        return sorted(valid, key=lambda x: x.timestamp)

    def get_high_risk_vehicles(
        self,
        as_of_timestamp: float,
        min_probability: float = 0.60,
    ) -> List[VehicleRiskPrediction]:
        """Returns all vehicles with defect probability >= min_probability up to `as_of_timestamp`."""
        valid = self.get_predictions_as_of(as_of_timestamp)
        return [p for p in valid if p.defect_probability >= min_probability]

    def get_medium_risk_vehicles(
        self,
        as_of_timestamp: float,
        low_threshold: float = 0.25,
        high_threshold: float = 0.60,
    ) -> List[VehicleRiskPrediction]:
        """Returns all vehicles in the medium risk exposure band."""
        valid = self.get_predictions_as_of(as_of_timestamp)
        return [p for p in valid if low_threshold <= p.defect_probability < high_threshold]

    def get_vehicle_risk_summary(
        self,
        as_of_timestamp: float,
    ) -> Dict[str, Any]:
        """Aggregates vehicle quality exposure statistics up to `as_of_timestamp`."""
        valid = self.get_predictions_as_of(as_of_timestamp)
        if not valid:
            return {
                "total_vehicles_evaluated": 0,
                "high_risk_count": 0,
                "medium_risk_count": 0,
                "low_risk_count": 0,
                "mean_defect_probability": 0.0,
                "max_defect_probability": 0.0,
                "high_risk_vehicle_ids": [],
            }

        probs = [p.defect_probability for p in valid]
        high_v = [p for p in valid if p.quality_exposure == "HIGH" or p.defect_probability >= 0.60]
        med_v = [p for p in valid if p.quality_exposure == "MEDIUM" or (0.25 <= p.defect_probability < 0.60)]
        low_v = [p for p in valid if p.quality_exposure == "LOW" and p.defect_probability < 0.25]

        return {
            "total_vehicles_evaluated": len(valid),
            "high_risk_count": len(high_v),
            "medium_risk_count": len(med_v),
            "low_risk_count": len(low_v),
            "mean_defect_probability": float(sum(probs) / len(probs)),
            "max_defect_probability": float(max(probs)),
            "high_risk_vehicle_ids": sorted([p.vehicle_id for p in high_v]),
        }
