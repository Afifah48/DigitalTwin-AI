"""
Two-sided Cumulative Sum (CUSUM) change detection module.

Accumulates small, persistent shifts in sensor telemetry while ignoring single-point
noise, detecting positive (upward) and negative (downward) shifts away from target means.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class CUSUMDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NONE = "NONE"


@dataclass
class CUSUMResult:
    """Output results and shift determination from a CUSUM step."""
    raw_value: float
    target_mean: float
    positive_sum: float
    negative_sum: float
    threshold: float
    drift: float
    detected_change: bool
    direction: str  # "POSITIVE", "NEGATIVE", or "NONE"
    step_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CUSUMDetector:
    """
    Two-sided tabular Cumulative Sum (CUSUM) quality control detector.

    Formulas:
        S_H[t] = max(0, S_H[t-1] + (x_t - target_mean - drift))
        S_L[t] = max(0, S_L[t-1] - (x_t - target_mean + drift))

    Alarm triggers when:
        S_H[t] > threshold  (Positive / Upward Shift)
        S_L[t] > threshold  (Negative / Downward Shift)
    """

    def __init__(
        self,
        target_mean: float = 0.0,
        drift: float = 0.5,
        threshold: float = 4.0,
        reset_on_alarm: bool = False,
    ) -> None:
        """
        Args:
            target_mean: Expected baseline reference mean value.
            drift: Allowance / slack parameter (k). Typically set to 0.5 * sigma or half the shift size to detect.
            threshold: Decision interval (h). Typically set to 4 to 5 * sigma.
            reset_on_alarm: If True, resets accumulator back to zero upon triggering an alarm.
        """
        self.target_mean = float(target_mean)
        self.drift = max(0.0, float(drift))
        self.threshold = max(0.0, float(threshold))
        self.reset_on_alarm = bool(reset_on_alarm)

        self.positive_sum: float = 0.0
        self.negative_sum: float = 0.0
        self.step_count: int = 0
        self.last_result: Optional[CUSUMResult] = None

    def reset(
        self,
        new_mean: Optional[float] = None,
        new_drift: Optional[float] = None,
        new_threshold: Optional[float] = None,
    ) -> None:
        """Resets the accumulators and optionally updates parameters."""
        if new_mean is not None:
            self.target_mean = float(new_mean)
        if new_drift is not None:
            self.drift = max(0.0, float(new_drift))
        if new_threshold is not None:
            self.threshold = max(0.0, float(new_threshold))

        self.positive_sum = 0.0
        self.negative_sum = 0.0
        self.step_count = 0
        self.last_result = None

    def update(self, value: float) -> CUSUMResult:
        """
        Ingests a new observation and updates two-sided accumulators.

        Args:
            value: Current observation from sensor.

        Returns:
            CUSUMResult detailing positive_sum, negative_sum, detected_change, and direction.
        """
        if value is None or math.isnan(value):
            v = self.target_mean
        else:
            v = float(value)

        self.step_count += 1

        # Calculate deviation from target
        deviation = v - self.target_mean

        # Update high (positive) and low (negative) accumulators
        self.positive_sum = max(0.0, self.positive_sum + (deviation - self.drift))
        self.negative_sum = max(0.0, self.negative_sum - (deviation + self.drift))

        pos_alarm = self.positive_sum > self.threshold
        neg_alarm = self.negative_sum > self.threshold
        detected = pos_alarm or neg_alarm

        if pos_alarm and neg_alarm:
            # In the rare event both cross, pick the larger accumulator
            direction = (
                CUSUMDirection.POSITIVE.value
                if self.positive_sum >= self.negative_sum
                else CUSUMDirection.NEGATIVE.value
            )
        elif pos_alarm:
            direction = CUSUMDirection.POSITIVE.value
        elif neg_alarm:
            direction = CUSUMDirection.NEGATIVE.value
        else:
            direction = CUSUMDirection.NONE.value

        result = CUSUMResult(
            raw_value=round(v, 4),
            target_mean=round(self.target_mean, 4),
            positive_sum=round(self.positive_sum, 4),
            negative_sum=round(self.negative_sum, 4),
            threshold=round(self.threshold, 4),
            drift=round(self.drift, 4),
            detected_change=detected,
            direction=direction,
            step_count=self.step_count,
        )

        if detected and self.reset_on_alarm:
            if pos_alarm:
                self.positive_sum = 0.0
            if neg_alarm:
                self.negative_sum = 0.0

        self.last_result = result
        return result


class StationCUSUMTracker:
    """Manages CUSUM detectors across all sensor channels for a station."""

    def __init__(
        self,
        station_id: str,
        drift_sigma_ratio: float = 0.5,
        threshold_sigma_ratio: float = 4.0,
        baseline_metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.station_id = station_id
        self.drift_sigma_ratio = drift_sigma_ratio
        self.threshold_sigma_ratio = threshold_sigma_ratio
        self.detectors: Dict[str, CUSUMDetector] = {}

        if baseline_metrics:
            self.configure_from_baseline(baseline_metrics)

    def configure_from_baseline(self, baseline_metrics: Dict[str, Any]) -> None:
        """Initializes or configures detectors from baseline statistics."""
        for metric_name, base_stat in baseline_metrics.items():
            if hasattr(base_stat, "mean") and hasattr(base_stat, "std"):
                mean = base_stat.mean
                std = max(base_stat.std, 0.1)
            elif isinstance(base_stat, dict):
                mean = base_stat.get("mean", 0.0)
                std = max(base_stat.get("std", 1.0), 0.1)
            else:
                continue

            drift = self.drift_sigma_ratio * std
            threshold = self.threshold_sigma_ratio * std

            if metric_name in self.detectors:
                self.detectors[metric_name].reset(
                    new_mean=mean,
                    new_drift=drift,
                    new_threshold=threshold,
                )
            else:
                self.detectors[metric_name] = CUSUMDetector(
                    target_mean=mean,
                    drift=drift,
                    threshold=threshold,
                )

    def update_station(self, telemetry: Dict[str, Any]) -> Dict[str, CUSUMResult]:
        """
        Updates all sensor detectors for the station with the latest telemetry values.

        Returns:
            Dictionary mapping metric name to CUSUMResult.
        """
        results: Dict[str, CUSUMResult] = {}
        for metric_name, val in telemetry.items():
            if val is None:
                continue
            try:
                numeric_val = float(val)
            except (ValueError, TypeError):
                continue

            if metric_name not in self.detectors:
                self.detectors[metric_name] = CUSUMDetector(
                    target_mean=numeric_val,
                    drift=max(0.2, abs(numeric_val) * 0.05),
                    threshold=max(1.0, abs(numeric_val) * 0.20),
                )

            results[metric_name] = self.detectors[metric_name].update(numeric_val)

        return results
