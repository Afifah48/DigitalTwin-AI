"""
Deviation calculation module for comparing real-time telemetry against statistical baselines.

Computes raw deltas, standardized z-scores, normalized feature deviations (0.0 - 1.0),
and weighted composite deviation scores per station.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from backend.analytics.baseline import MetricBaseline, StationBaseline

# Default weights applied across telemetry metrics when computing station composite deviation
DEFAULT_METRIC_WEIGHTS: Dict[str, float] = {
    "cycle_time": 0.20,
    "utilization": 0.15,
    "queue": 0.10,
    "WIP": 0.10,
    "temperature": 0.15,
    "vibration": 0.15,
    "motor_current": 0.10,
    "current_variance": 0.05,
}

# Z-score anomaly threshold (e.g. standard 2.5 sigma or 3 sigma)
DEFAULT_ANOMALY_Z_THRESHOLD: float = 2.5


@dataclass
class MetricDeviation:
    """Deviation analytics for an individual sensor or metric."""
    metric_name: str
    observed: float
    expected_mean: float
    expected_std: float
    delta: float
    z_score: float
    deviation_score: float  # Normalized to [0.0, 1.0]
    is_anomalous: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StationDeviation:
    """Comprehensive deviation summary for a machine station."""
    station_id: str
    metric_deviations: Dict[str, MetricDeviation] = field(default_factory=dict)
    composite_deviation: float = 0.0  # Overall station deviation score [0.0, 1.0]
    highest_deviation_metric: Optional[str] = None
    anomalous_metrics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "station_id": self.station_id,
            "composite_deviation": self.composite_deviation,
            "highest_deviation_metric": self.highest_deviation_metric,
            "anomalous_metrics": list(self.anomalous_metrics),
            "metric_deviations": {
                k: v.to_dict() for k, v in self.metric_deviations.items()
            },
        }


def calculate_delta(observed: float, baseline: float) -> float:
    """
    Calculates raw difference between observed and baseline values:
    delta = observed - baseline
    """
    if observed is None or baseline is None or math.isnan(observed) or math.isnan(baseline):
        return 0.0
    return float(observed) - float(baseline)


def calculate_z_score(
    observed: float,
    mean: float,
    std: float,
    min_std: float = 1e-4,
) -> float:
    """
    Calculates standardized z-score:
    z = (observed - mean) / max(std, min_std)

    Clamps output to [-20.0, 20.0] for numerical safety.
    """
    if observed is None or mean is None or math.isnan(observed) or math.isnan(mean):
        return 0.0
    safe_std = max(abs(float(std)) if std is not None and not math.isnan(std) else 0.0, min_std)
    z = (float(observed) - float(mean)) / safe_std
    return max(min(z, 20.0), -20.0)


def normalize_z_to_deviation(z_score: float, scaling_factor: float = 2.5) -> float:
    """
    Normalizes a standardized z-score into a continuous deviation score in [0.0, 1.0].
    Uses hyperbolic tangent curve: d = tanh(|z| / scaling_factor).
    - |z| = 0.0 -> 0.00
    - |z| = 1.0 -> 0.38
    - |z| = 2.0 -> 0.66
    - |z| = 3.0 -> 0.83
    - |z| >= 4.0 -> 0.93 - 1.00
    """
    if z_score is None or math.isnan(z_score):
        return 0.0
    abs_z = abs(float(z_score))
    scale = max(scaling_factor, 1e-4)
    normalized = math.tanh(abs_z / scale)
    return max(0.0, min(1.0, round(normalized, 6)))


def calculate_deviation_score(
    observed_metrics: Dict[str, Any],
    station_baseline: Optional[StationBaseline],
    weights: Optional[Dict[str, float]] = None,
    anomaly_z_threshold: float = DEFAULT_ANOMALY_Z_THRESHOLD,
) -> StationDeviation:
    """
    Compares observed station telemetry against its reference baseline.
    Computes per-metric deltas, z-scores, normalized deviations, and combined weighted deviation.

    Args:
        observed_metrics: Dictionary of current telemetry values for the station.
        station_baseline: Reference StationBaseline object (optional).
        weights: Optional dictionary of feature weights for composite scoring.
        anomaly_z_threshold: Z-score magnitude considered anomalous.

    Returns:
        StationDeviation object containing granular and aggregated deviation metrics.
    """
    station_id = station_baseline.station_id if station_baseline else "UNKNOWN"
    if not observed_metrics:
        return StationDeviation(station_id=station_id)

    active_weights = dict(DEFAULT_METRIC_WEIGHTS)
    if weights:
        active_weights.update(weights)

    metric_devs: Dict[str, MetricDeviation] = {}
    anomalous: List[str] = []
    highest_metric: Optional[str] = None
    max_dev_score = -1.0

    total_weight = 0.0
    weighted_dev_sum = 0.0

    for metric_name, raw_val in observed_metrics.items():
        if raw_val is None:
            continue
        try:
            val = float(raw_val)
        except (ValueError, TypeError):
            continue

        base_stat: Optional[MetricBaseline] = None
        if station_baseline:
            base_stat = station_baseline.get_metric(metric_name)

        if base_stat and base_stat.count > 0:
            exp_mean = base_stat.mean
            exp_std = base_stat.std
        else:
            exp_mean = val
            exp_std = 1.0

        delta = calculate_delta(val, exp_mean)
        z = calculate_z_score(val, exp_mean, exp_std)
        dev_score = normalize_z_to_deviation(z)
        is_anomaly = abs(z) >= anomaly_z_threshold

        metric_devs[metric_name] = MetricDeviation(
            metric_name=metric_name,
            observed=round(val, 4),
            expected_mean=round(exp_mean, 4),
            expected_std=round(exp_std, 4),
            delta=round(delta, 4),
            z_score=round(z, 4),
            deviation_score=dev_score,
            is_anomalous=is_anomaly,
        )

        if is_anomaly:
            anomalous.append(metric_name)

        if dev_score > max_dev_score:
            max_dev_score = dev_score
            highest_metric = metric_name

        w = active_weights.get(metric_name, 0.10)
        weighted_dev_sum += dev_score * w
        total_weight += w

    composite_dev = (
        round(weighted_dev_sum / total_weight, 6) if total_weight > 0 else 0.0
    )

    return StationDeviation(
        station_id=station_id,
        metric_deviations=metric_devs,
        composite_deviation=composite_dev,
        highest_deviation_metric=highest_metric,
        anomalous_metrics=anomalous,
    )
