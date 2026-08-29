"""
Sensor confidence and telemetry data quality calculation module.

Evaluates sensor count, missing data rates, channel coverage, and data freshness to
generate a reliable 0.0 to 1.0 confidence score.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, Optional, Sequence, Union

# Default weights for confidence components
DEFAULT_CONFIDENCE_WEIGHTS = {
    "coverage": 0.35,
    "completeness": 0.30,  # 1.0 - missing_rate
    "freshness": 0.25,
    "historical_accuracy": 0.10,  # 1.0 - historical_error
}


@dataclass
class SensorConfidenceResult:
    """Sensor quality and confidence assessment."""
    sensor_count: int
    missing_rate: float       # [0.0, 1.0] (0.0 = perfect, 1.0 = all missing)
    coverage: float           # [0.0, 1.0] (reporting_sensors / expected_sensors)
    data_freshness: float     # [0.0, 1.0] (1.0 = fresh, 0.0 = stale)
    sensor_confidence: float  # [0.0, 1.0] Composite score
    historical_error_rate: float = 0.0
    reporting_sensors: int = 0
    expected_sensors: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_data_freshness(
    age_seconds: float,
    max_acceptable_staleness: float = 10.0,
) -> float:
    """
    Computes data freshness score in [0.0, 1.0].
    - age <= 1.0 * max_acceptable: freshness = 1.0
    - 1.0 * max < age <= 2.0 * max: linear decay from 1.0 to 0.0
    - age > 2.0 * max: freshness = 0.0
    """
    if age_seconds is None or math.isnan(age_seconds) or age_seconds < 0:
        return 1.0

    max_stale = max(0.1, float(max_acceptable_staleness))
    if age_seconds <= max_stale:
        return 1.0
    elif age_seconds >= 2.0 * max_stale:
        return 0.0
    else:
        # Linear decay between 1x and 2x max staleness
        return max(0.0, min(1.0, 1.0 - (age_seconds - max_stale) / max_stale))


def calculate_sensor_confidence(
    expected_sensors: Union[int, Sequence[str], Iterable[str]],
    reporting_telemetry: Optional[Dict[str, Any]] = None,
    missing_rate: Optional[float] = None,
    coverage: Optional[float] = None,
    data_age_seconds: float = 0.0,
    max_staleness_seconds: float = 10.0,
    historical_error_rate: float = 0.0,
    weights: Optional[Dict[str, float]] = None,
) -> SensorConfidenceResult:
    """
    Calculates overall sensor telemetry confidence score in [0.0, 1.0].

    Can be invoked either by passing the raw telemetry dictionary:
        calculate_sensor_confidence(expected_sensors=['temp', 'vib', ...], reporting_telemetry={...})
    Or with pre-calculated rates:
        calculate_sensor_confidence(expected_sensors=8, coverage=0.875, missing_rate=0.0)

    Args:
        expected_sensors: List of expected sensor keys or total expected sensor count.
        reporting_telemetry: Dictionary of sensor readings in the current payload.
        missing_rate: Explicit missing value rate [0.0, 1.0] (optional).
        coverage: Explicit coverage ratio [0.0, 1.0] (optional).
        data_age_seconds: Seconds elapsed since timestamp of telemetry.
        max_staleness_seconds: Threshold for staleness penalization.
        historical_error_rate: Historical sensor fault or dropout rate.
        weights: Optional customization for component weights.

    Returns:
        SensorConfidenceResult containing granular metrics and aggregate confidence.
    """
    active_weights = dict(DEFAULT_CONFIDENCE_WEIGHTS)
    if weights:
        active_weights.update(weights)

    # Resolve expected and reporting sensor counts
    if isinstance(expected_sensors, (list, tuple, set)):
        expected_keys = list(expected_sensors)
        num_expected = len(expected_keys)
    else:
        expected_keys = []
        num_expected = max(1, int(expected_sensors))

    if reporting_telemetry is not None:
        if expected_keys:
            valid_keys = [k for k in expected_keys if k in reporting_telemetry and reporting_telemetry[k] is not None]
            num_reporting = len(valid_keys)
            computed_coverage = num_reporting / num_expected
            total_expected_values = num_expected
            missing_count = sum(1 for k in expected_keys if k not in reporting_telemetry or reporting_telemetry[k] is None)
            computed_missing_rate = missing_count / total_expected_values
        else:
            present_keys = [k for k, v in reporting_telemetry.items() if v is not None]
            num_reporting = len(present_keys)
            total_keys = len(reporting_telemetry)
            computed_coverage = min(1.0, num_reporting / max(1, num_expected))
            missing_count = sum(1 for v in reporting_telemetry.values() if v is None)
            computed_missing_rate = missing_count / max(1, total_keys)
    else:
        num_reporting = num_expected if coverage is None else int(round(coverage * num_expected))
        computed_coverage = float(coverage) if coverage is not None else 1.0
        computed_missing_rate = float(missing_rate) if missing_rate is not None else 0.0

    final_coverage = max(0.0, min(1.0, computed_coverage))
    final_missing_rate = max(0.0, min(1.0, computed_missing_rate))
    freshness = calculate_data_freshness(data_age_seconds, max_staleness_seconds)
    hist_err = max(0.0, min(1.0, float(historical_error_rate)))

    completeness = 1.0 - final_missing_rate
    accuracy = 1.0 - hist_err

    # Weighted composite score
    w_cov = active_weights.get("coverage", 0.35)
    w_comp = active_weights.get("completeness", 0.30)
    w_fresh = active_weights.get("freshness", 0.25)
    w_acc = active_weights.get("historical_accuracy", 0.10)
    w_total = w_cov + w_comp + w_fresh + w_acc

    composite = (
        w_cov * final_coverage
        + w_comp * completeness
        + w_fresh * freshness
        + w_acc * accuracy
    ) / max(w_total, 1e-4)

    final_confidence = max(0.0, min(1.0, round(composite, 4)))

    return SensorConfidenceResult(
        sensor_count=num_reporting,
        missing_rate=round(final_missing_rate, 4),
        coverage=round(final_coverage, 4),
        data_freshness=round(freshness, 4),
        sensor_confidence=final_confidence,
        historical_error_rate=round(hist_err, 4),
        reporting_sensors=num_reporting,
        expected_sensors=num_expected,
    )
