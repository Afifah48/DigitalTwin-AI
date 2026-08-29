"""
Vehicle Quality Feature Engineering and Preprocessing Module.

Extracts rich, vehicle-level aggregated operational exposure features
from historical telemetry, Phase 4 anomaly detection, and Phase 5 bottleneck state.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler

from backend.quality.phase4_adapter import Phase4Adapter
from backend.quality.phase5_adapter import Phase5Adapter
from backend.quality.schemas import VehicleObservation
from backend.quality.temporal import filter_by_timestamp

# Canonical Vehicle Feature Schema List (Deterministic order)
QUALITY_FEATURE_NAMES: List[str] = [
    # Vehicle metadata / categorical one-hot encodings
    "model_Sedan",
    "model_SUV",
    "model_Truck",
    "model_Coupe",
    "variant_Base",
    "variant_Premium",
    "variant_EV",
    "variant_Sport",
    # Duration & throughput timing
    "station_exposure_duration",
    "total_production_time",
    "stations_visited_count",
    # Cycle time exposure
    "cycle_time_mean",
    "cycle_time_max",
    "cycle_time_deviation_mean",
    "cycle_time_deviation_max",
    "cycle_time_deviation_cumulative",
    # Queue & buffer exposure
    "queue_exposure_mean",
    "queue_exposure_max",
    "queue_exposure_cumulative",
    "buffer_exposure_mean",
    "buffer_exposure_max",
    # Environmental & physical sensor exposures
    "vibration_mean",
    "vibration_max",
    "temperature_mean",
    "temperature_max",
    "motor_current_mean",
    "motor_current_max",
    "motor_current_variance_mean",
    "motor_current_variance_max",
    # Specific station S3 torque / fastening exposure
    "S3_visited",
    "S3_torque_exposure",
    "S3_current_variance_exposure",
    # Machine state exposure
    "state_blocked_count",
    "state_starved_count",
    "state_down_fault_count",
    "state_warning_count",
    "machine_state_abnormal_ratio",
    # Phase 4 Anomaly exposure
    "phase4_anomaly_score_mean",
    "phase4_anomaly_score_max",
    "phase4_anomalies_detected_count",
    "phase4_high_severity_count",
    # Phase 5 Bottleneck exposure
    "phase5_bottleneck_risk_mean",
    "phase5_bottleneck_risk_max",
    "phase5_propagation_risk_max",
    # Composite abnormal event count
    "number_of_abnormal_events",
]

CATEGORICAL_MODELS = ["Sedan", "SUV", "Truck", "Coupe"]
CATEGORICAL_VARIANTS = ["Base", "Premium", "EV", "Sport"]


def extract_vehicle_features(
    vehicle_id: str,
    vehicle_history: Sequence[Union[VehicleObservation, Dict[str, Any]]],
    as_of_timestamp: float,
    phase4_adapter: Optional[Phase4Adapter] = None,
    phase5_adapter: Optional[Phase5Adapter] = None,
) -> Dict[str, float]:
    """
    Constructs a vehicle-level feature dictionary representing all production conditions
    experienced by the vehicle strictly on or before `as_of_timestamp`.

    Temporal Rule: Records after `as_of_timestamp` are strictly filtered out before aggregation.
    """
    # 1. Strict Temporal Filtering
    valid_records = filter_by_timestamp(vehicle_history, as_of_timestamp)
    if not valid_records:
        # Default zero-vector for vehicle with no prior records at as_of_timestamp
        return {feat_name: 0.0 for feat_name in QUALITY_FEATURE_NAMES}

    # Normalize to dicts
    records: List[Dict[str, Any]] = [
        r.to_dict() if hasattr(r, "to_dict") else dict(r) for r in valid_records
    ]

    first_record = records[0]
    latest_record = records[-1]

    v_model = str(first_record.get("vehicle_model", "Sedan"))
    v_variant = str(first_record.get("vehicle_variant", "Base"))

    # Model & Variant One-Hot Encodings
    feats: Dict[str, float] = {}
    for m in CATEGORICAL_MODELS:
        feats[f"model_{m}"] = 1.0 if v_model.lower() == m.lower() else 0.0
    for v in CATEGORICAL_VARIANTS:
        feats[f"variant_{v}"] = 1.0 if v_variant.lower() == v.lower() else 0.0

    # Timing & Stations
    timestamps = [float(r.get("timestamp", 0.0)) for r in records]
    durations = [float(r.get("duration", r.get("cycle_time", 50.0))) for r in records]
    stations = [str(r.get("station_id", "")) for r in records]
    unique_stations = list(dict.fromkeys(stations))

    feats["station_exposure_duration"] = float(sum(durations))
    feats["total_production_time"] = float(max(0.0, as_of_timestamp - min(timestamps)))
    feats["stations_visited_count"] = float(len(unique_stations))

    # Cycle Time Metrics
    cycle_times = [float(r.get("cycle_time", 50.0)) for r in records]
    cycle_deltas = [float(r.get("cycle_time_delta", 0.0)) for r in records]

    feats["cycle_time_mean"] = float(np.mean(cycle_times))
    feats["cycle_time_max"] = float(np.max(cycle_times))
    feats["cycle_time_deviation_mean"] = float(np.mean(cycle_deltas))
    feats["cycle_time_deviation_max"] = float(np.max(cycle_deltas))
    feats["cycle_time_deviation_cumulative"] = float(np.sum(np.maximum(0.0, cycle_deltas)))

    # Queue & Buffer Exposure
    queues = [float(r.get("queue_length", r.get("queue", 0))) for r in records]
    buffers = [float(r.get("buffer_occupancy", r.get("occupancy", 0.0))) for r in records]

    feats["queue_exposure_mean"] = float(np.mean(queues))
    feats["queue_exposure_max"] = float(np.max(queues))
    feats["queue_exposure_cumulative"] = float(np.sum(queues))
    feats["buffer_exposure_mean"] = float(np.mean(buffers))
    feats["buffer_exposure_max"] = float(np.max(buffers))

    # Environmental & Physical Sensors (handling missing values with nominal imputation)
    vibrations = [float(r.get("vibration", 0.09) or 0.09) for r in records]
    temperatures = [float(r.get("temperature", 62.0) or 62.0) for r in records]
    currents = [float(r.get("motor_current", 4.8) or 4.8) for r in records]
    current_vars = [float(r.get("current_variance", 0.05) or 0.05) for r in records]

    feats["vibration_mean"] = float(np.mean(vibrations))
    feats["vibration_max"] = float(np.max(vibrations))
    feats["temperature_mean"] = float(np.mean(temperatures))
    feats["temperature_max"] = float(np.max(temperatures))
    feats["motor_current_mean"] = float(np.mean(currents))
    feats["motor_current_max"] = float(np.max(currents))
    feats["motor_current_variance_mean"] = float(np.mean(current_vars))
    feats["motor_current_variance_max"] = float(np.max(current_vars))

    # S3 Torque & Fastening Exposure
    s3_records = [r for r in records if r.get("station_id") == "S3"]
    if s3_records:
        feats["S3_visited"] = 1.0
        # If explicit torque exists in telemetry use it, otherwise use motor current * current_variance proxy
        s3_torques = [float(r.get("torque", float(r.get("motor_current", 5.2) or 5.2) * (1.0 + float(r.get("current_variance", 0.05) or 0.05))) or 0.0) for r in s3_records]
        s3_cvs = [float(r.get("current_variance", 0.05) or 0.05) for r in s3_records]
        feats["S3_torque_exposure"] = float(np.max(s3_torques))
        feats["S3_current_variance_exposure"] = float(np.max(s3_cvs))
    else:
        feats["S3_visited"] = 0.0
        feats["S3_torque_exposure"] = 0.0
        feats["S3_current_variance_exposure"] = 0.0

    # Machine State Exposure
    states = [str(r.get("machine_state", r.get("state", "RUNNING"))).upper() for r in records]
    blocked_c = sum(1 for s in states if s == "BLOCKED")
    starved_c = sum(1 for s in states if s == "STARVED")
    down_fault_c = sum(1 for s in states if s in ("DOWN", "FAULT", "ERROR"))
    warning_c = sum(1 for s in states if s in ("WARNING", "MAINTENANCE"))

    feats["state_blocked_count"] = float(blocked_c)
    feats["state_starved_count"] = float(starved_c)
    feats["state_down_fault_count"] = float(down_fault_c)
    feats["state_warning_count"] = float(warning_c)
    feats["machine_state_abnormal_ratio"] = float((blocked_c + starved_c + down_fault_c + warning_c) / len(states))

    # Phase 4 Anomaly Integration
    p4_scores: List[float] = []
    p4_detected = 0
    p4_high_sev = 0

    if phase4_adapter is not None:
        for st_id in unique_stations:
            summary = phase4_adapter.get_station_summary(station_id=st_id, as_of_timestamp=as_of_timestamp)
            p4_scores.append(summary.max_anomaly_score)
            p4_detected += summary.anomaly_detected_count
            if summary.severity_level == "HIGH":
                p4_high_sev += 1

    feats["phase4_anomaly_score_mean"] = float(np.mean(p4_scores)) if p4_scores else 0.0
    feats["phase4_anomaly_score_max"] = float(np.max(p4_scores)) if p4_scores else 0.0
    feats["phase4_anomalies_detected_count"] = float(p4_detected)
    feats["phase4_high_severity_count"] = float(p4_high_sev)

    # Phase 5 Bottleneck Integration
    p5_risks: List[float] = []
    p5_prop_risks: List[float] = []

    if phase5_adapter is not None:
        for st_id in unique_stations:
            p5_exp = phase5_adapter.get_station_bottleneck_exposure(station_id=st_id, as_of_timestamp=as_of_timestamp)
            p5_risks.append(p5_exp["max_bottleneck_risk"])
            p5_prop_risks.append(p5_exp["max_propagation_risk"])

    feats["phase5_bottleneck_risk_mean"] = float(np.mean(p5_risks)) if p5_risks else 0.0
    feats["phase5_bottleneck_risk_max"] = float(np.max(p5_risks)) if p5_risks else 0.0
    feats["phase5_propagation_risk_max"] = float(np.max(p5_prop_risks)) if p5_prop_risks else 0.0

    # Composite Number of Abnormal Events (without double counting)
    # Counts discrete abnormal occurrences experienced by this vehicle
    abnormal_events = (
        down_fault_c
        + warning_c
        + p4_detected
        + (1 if feats["queue_exposure_max"] >= 8 else 0)
        + (1 if feats["buffer_exposure_max"] >= 9.0 else 0)
        + (1 if feats["vibration_max"] >= 0.25 else 0)
        + (1 if feats["motor_current_variance_max"] >= 0.20 else 0)
    )
    feats["number_of_abnormal_events"] = float(abnormal_events)

    return feats


def feature_dict_to_array(
    features_dict: Dict[str, float],
    feature_names: Optional[List[str]] = None,
) -> np.ndarray:
    """Converts feature dict to strict 1D numpy array in canonical schema order."""
    names = feature_names or QUALITY_FEATURE_NAMES
    return np.array([float(features_dict.get(k, 0.0)) for k in names], dtype=np.float32)


class VehicleFeaturePreprocessor:
    """
    Leakage-free Feature Preprocessor for Phase 6.

    Fits standard scaling on training data ONLY, saves configuration to JSON,
    and applies deterministic transformations during inference.
    """

    def __init__(self, feature_names: Optional[List[str]] = None) -> None:
        self.feature_names: List[str] = feature_names or list(QUALITY_FEATURE_NAMES)
        self.scaler: StandardScaler = StandardScaler()
        self.is_fitted: bool = False

    def fit(self, X: np.ndarray) -> VehicleFeaturePreprocessor:
        """Fits standard scaler exclusively on training matrix X."""
        X_arr = np.asarray(X, dtype=np.float32)
        self.scaler.fit(X_arr)
        self.is_fitted = True
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Standardizes feature matrix X using fitted parameters."""
        if not self.is_fitted:
            raise RuntimeError("Preprocessor must be fitted on training data before transform!")
        X_arr = np.asarray(X, dtype=np.float32)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1)
        return self.scaler.transform(X_arr).astype(np.float32)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)

    def save(self, filepath_joblib: str, filepath_schema_json: Optional[str] = None) -> None:
        """Saves the fitted preprocessor and schema definition."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath_joblib)), exist_ok=True)
        joblib.dump(self, filepath_joblib)

        if filepath_schema_json:
            schema_data = {
                "feature_names": self.feature_names,
                "num_features": len(self.feature_names),
                "categorical_models": CATEGORICAL_MODELS,
                "categorical_variants": CATEGORICAL_VARIANTS,
                "means": self.scaler.mean_.tolist() if self.is_fitted else [],
                "scales": self.scaler.scale_.tolist() if self.is_fitted else [],
            }
            with open(filepath_schema_json, "w") as f:
                json.dump(schema_data, f, indent=2)

    @classmethod
    def load(cls, filepath_joblib: str) -> VehicleFeaturePreprocessor:
        """Loads fitted preprocessor from disk."""
        return joblib.load(filepath_joblib)
