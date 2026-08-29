"""
Feature extraction and normalization pipeline for ML anomaly detection.

Extracts the 11 standardized Phase 4 telemetry features and handles deterministic
categorical machine-state encoding and leakage-free normalization scaling.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

# Exact 11 features required for Phase 4
ANOMALY_FEATURE_NAMES: List[str] = [
    "cycle_time",
    "cycle_time_delta",
    "utilization",
    "queue_length",
    "wip",
    "temperature",
    "vibration",
    "motor_current",
    "current_variance",
    "buffer_occupancy",
    "machine_state_encoded",
]

# Deterministic categorical mapping
MACHINE_STATE_ENCODING: Dict[str, int] = {
    "RUNNING": 0,
    "IDLE": 1,
    "BLOCKED": 2,
    "STARVED": 3,
    "DOWN": 4,
    "FAULT": 4,
    "ERROR": 4,
    "OFFLINE": 4,
    "MAINTENANCE": 5,
    "SETUP": 5,
    "WARNING": 0,
    "UNKNOWN": 1,
}


def encode_machine_state(state_value: Union[str, int, float, None]) -> int:
    """Encodes categorical machine state string to an integer index [0, 5]."""
    if state_value is None:
        return 0
    if isinstance(state_value, (int, float)) and not math.isnan(state_value):
        idx = int(state_value)
        return max(0, min(5, idx))
    state_str = str(state_value).strip().upper()
    return MACHINE_STATE_ENCODING.get(state_str, 0)


def extract_station_features(
    station_telemetry: Dict[str, Any],
    station_baseline: Optional[Any] = None,
    connected_buffer_occupancy: float = 0.0,
) -> np.ndarray:
    """
    Converts a single station's raw telemetry dictionary into the 11-dimensional feature vector.

    Args:
        station_telemetry: Raw sensor and metric readings for the station.
        station_baseline: Optional StationBaseline object to calculate cycle_time_delta.
        connected_buffer_occupancy: Occupancy / pressure of immediate buffer.

    Returns:
        1D numpy array of shape (11,) with float64 values.
    """
    # 1. cycle_time
    cycle_time = float(station_telemetry.get("cycle_time", 0.0) or 0.0)

    # 2. cycle_time_delta
    baseline_cycle = 0.0
    if station_baseline:
        if hasattr(station_baseline, "get_metric"):
            m = station_baseline.get_metric("cycle_time")
            if m:
                baseline_cycle = m.mean
        elif isinstance(station_baseline, dict) and "cycle_time" in station_baseline:
            baseline_cycle = float(station_baseline["cycle_time"].get("mean", 0.0))

    if baseline_cycle > 0:
        cycle_time_delta = cycle_time - baseline_cycle
    else:
        cycle_time_delta = float(station_telemetry.get("cycle_time_delta", 0.0) or 0.0)

    # 3. utilization
    utilization = float(station_telemetry.get("utilization", 0.0) or 0.0)

    # 4. queue_length
    queue_length = float(
        station_telemetry.get("queue_length", station_telemetry.get("queue", 0.0)) or 0.0
    )

    # 5. wip
    wip = float(
        station_telemetry.get("wip", station_telemetry.get("WIP", 0.0)) or 0.0
    )

    # 6. temperature
    temperature = float(station_telemetry.get("temperature", 0.0) or 0.0)

    # 7. vibration
    vibration = float(station_telemetry.get("vibration", 0.0) or 0.0)

    # 8. motor_current
    motor_current = float(station_telemetry.get("motor_current", 0.0) or 0.0)

    # 9. current_variance
    current_variance = float(station_telemetry.get("current_variance", 0.0) or 0.0)

    # 10. buffer_occupancy
    buffer_occ = float(
        station_telemetry.get("buffer_occupancy", connected_buffer_occupancy) or 0.0
    )

    # 11. machine_state_encoded
    raw_state = station_telemetry.get("machine_state", station_telemetry.get("state", "RUNNING"))
    machine_state_encoded = float(encode_machine_state(raw_state))

    features = [
        cycle_time,
        cycle_time_delta,
        utilization,
        queue_length,
        wip,
        temperature,
        vibration,
        motor_current,
        current_variance,
        buffer_occ,
        machine_state_encoded,
    ]

    # Handle any NaN/Inf values with fallback zeros
    clean_features = [0.0 if (math.isnan(x) or math.isinf(x)) else float(x) for x in features]
    return np.array(clean_features, dtype=np.float32)


class FeatureScaler:
    """
    StandardScaler implementing (x - mean) / std normalization.

    Fitted strictly on training simulation runs to prevent data leakage.
    """

    def __init__(self, feature_names: Optional[List[str]] = None) -> None:
        self.feature_names = feature_names or list(ANOMALY_FEATURE_NAMES)
        self.mean: Optional[np.ndarray] = None
        self.std: Optional[np.ndarray] = None
        self.n_features: int = len(self.feature_names)
        self.is_fitted: bool = False

    def fit(self, X: Union[np.ndarray, List[List[float]]]) -> "FeatureScaler":
        """Computes feature-wise mean and standard deviation from training data."""
        data = np.asarray(X, dtype=np.float32)
        if data.ndim == 3:
            # Sequence data (N, T, F) -> flatten to (N*T, F)
            data = data.reshape(-1, data.shape[-1])

        if data.ndim != 2:
            raise ValueError(f"Expected 2D or 3D array for scaling, got shape {data.shape}")

        self.mean = np.mean(data, axis=0)
        raw_std = np.std(data, axis=0)
        # Avoid zero division with epsilon clamping
        self.std = np.where(raw_std < 1e-4, 1.0, raw_std)
        self.n_features = data.shape[1]
        self.is_fitted = True
        return self

    def transform(self, X: Union[np.ndarray, List[List[float]]]) -> np.ndarray:
        """Standardizes input features using fitted training statistics."""
        if not self.is_fitted or self.mean is None or self.std is None:
            raise RuntimeError("FeatureScaler must be fitted before transforming data.")

        data = np.asarray(X, dtype=np.float32)
        # Replace any NaNs in input with mean values
        nan_mask = np.isnan(data)
        if np.any(nan_mask):
            if data.ndim == 2:
                data = np.where(nan_mask, self.mean, data)
            elif data.ndim == 3:
                data = np.where(nan_mask, self.mean[np.newaxis, np.newaxis, :], data)

        return (data - self.mean) / self.std

    def fit_transform(self, X: Union[np.ndarray, List[List[float]]]) -> np.ndarray:
        """Fits scaler on data and returns transformed features."""
        return self.fit(X).transform(X)

    def inverse_transform(self, X_scaled: Union[np.ndarray, List[List[float]]]) -> np.ndarray:
        """Reconstructs original feature values from normalized space."""
        if not self.is_fitted or self.mean is None or self.std is None:
            raise RuntimeError("FeatureScaler must be fitted before inverse transform.")
        data = np.asarray(X_scaled, dtype=np.float32)
        return (data * self.std) + self.mean

    def to_dict(self) -> Dict[str, Any]:
        """Serializes scaler parameters to dictionary."""
        return {
            "feature_names": self.feature_names,
            "mean": self.mean.tolist() if self.mean is not None else [],
            "std": self.std.tolist() if self.std is not None else [],
            "is_fitted": self.is_fitted,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureScaler":
        """Reconstructs scaler from dictionary."""
        scaler = cls(feature_names=data.get("feature_names", ANOMALY_FEATURE_NAMES))
        if data.get("is_fitted", False) and data.get("mean") and data.get("std"):
            scaler.mean = np.array(data["mean"], dtype=np.float32)
            scaler.std = np.array(data["std"], dtype=np.float32)
            scaler.n_features = len(scaler.mean)
            scaler.is_fitted = True
        return scaler

    def save(self, file_path: str) -> None:
        """Saves scaler parameters to a JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, file_path: str) -> "FeatureScaler":
        """Loads scaler parameters from a JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
