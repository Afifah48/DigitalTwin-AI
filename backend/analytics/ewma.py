"""
Exponentially Weighted Moving Average (EWMA) detector module.

Smooths telemetry over time and detects gradual drift and statistical process control
threshold crossings across station sensors.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class EWMAResult:
    """Output state and anomaly determination from an EWMA step."""
    raw_value: float
    current_ewma: float
    target_mean: float
    deviation: float
    z_score: float
    threshold: float
    threshold_crossed: bool
    step_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EWMADetector:
    """
    Exponentially Weighted Moving Average (EWMA) change and drift detector.

    Formula:
        S_t = alpha * x_t + (1 - alpha) * S_{t-1}

    Theoretical variance of EWMA statistic:
        sigma_{ewma}^2 = sigma_0^2 * (alpha / (2 - alpha)) * [1 - (1 - alpha)^{2t}]
    """

    def __init__(
        self,
        alpha: float = 0.2,
        target_mean: float = 0.0,
        std: float = 1.0,
        threshold: float = 3.0,
        min_std: float = 1e-4,
    ) -> None:
        """
        Args:
            alpha: Smoothing weight [0.01, 1.0]. Lower values emphasize historical smoothing.
            target_mean: Expected baseline reference mean value.
            std: Expected baseline standard deviation.
            threshold: Multiplier for control limits (standard deviations).
            min_std: Minimum allowed standard deviation to avoid zero division.
        """
        self.alpha = max(0.001, min(1.0, float(alpha)))
        self.target_mean = float(target_mean)
        self.std = max(abs(float(std)), min_std)
        self.threshold = max(0.0, float(threshold))
        self.min_std = min_std

        self.current_ewma: Optional[float] = None
        self.step_count: int = 0
        self.last_result: Optional[EWMAResult] = None

    def reset(self, new_mean: Optional[float] = None, new_std: Optional[float] = None) -> None:
        """Resets the internal detector state."""
        if new_mean is not None:
            self.target_mean = float(new_mean)
        if new_std is not None:
            self.std = max(abs(float(new_std)), self.min_std)
        self.current_ewma = None
        self.step_count = 0
        self.last_result = None

    def update(self, value: float) -> EWMAResult:
        """
        Ingests a new observation and computes the updated EWMA, deviation, and alarm state.

        Args:
            value: Current observation from sensor.

        Returns:
            EWMAResult with updated EWMA, deviation, z-score, and threshold_crossed flag.
        """
        if value is None or math.isnan(value):
            v = self.current_ewma if self.current_ewma is not None else self.target_mean
        else:
            v = float(value)

        self.step_count += 1

        if self.current_ewma is None:
            # Initialization on first observation
            self.current_ewma = v
        else:
            self.current_ewma = self.alpha * v + (1.0 - self.alpha) * self.current_ewma

        # Calculate deviation from target baseline mean
        deviation = self.current_ewma - self.target_mean

        # Time-dependent standard error of EWMA
        factor = (self.alpha / (2.0 - self.alpha)) * (1.0 - (1.0 - self.alpha) ** (2 * self.step_count))
        sigma_ewma = self.std * math.sqrt(max(1e-6, factor))

        z_score = deviation / max(sigma_ewma, self.min_std)
        threshold_crossed = abs(z_score) > self.threshold

        result = EWMAResult(
            raw_value=round(v, 4),
            current_ewma=round(self.current_ewma, 4),
            target_mean=round(self.target_mean, 4),
            deviation=round(deviation, 4),
            z_score=round(z_score, 4),
            threshold=round(self.threshold, 4),
            threshold_crossed=threshold_crossed,
            step_count=self.step_count,
        )
        self.last_result = result
        return result


class StationEWMATracker:
    """Manages EWMA detectors across all sensor channels for a station."""

    def __init__(
        self,
        station_id: str,
        alpha: float = 0.2,
        threshold: float = 3.0,
        baseline_metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.station_id = station_id
        self.alpha = alpha
        self.threshold = threshold
        self.detectors: Dict[str, EWMADetector] = {}

        if baseline_metrics:
            self.configure_from_baseline(baseline_metrics)

    def configure_from_baseline(self, baseline_metrics: Dict[str, Any]) -> None:
        """Initializes or updates detectors with baseline target means and standard deviations."""
        for metric_name, base_stat in baseline_metrics.items():
            if hasattr(base_stat, "mean") and hasattr(base_stat, "std"):
                mean = base_stat.mean
                std = base_stat.std
            elif isinstance(base_stat, dict):
                mean = base_stat.get("mean", 0.0)
                std = base_stat.get("std", 1.0)
            else:
                continue

            if metric_name in self.detectors:
                self.detectors[metric_name].reset(new_mean=mean, new_std=std)
            else:
                self.detectors[metric_name] = EWMADetector(
                    alpha=self.alpha,
                    target_mean=mean,
                    std=std,
                    threshold=self.threshold,
                )

    def update_station(self, telemetry: Dict[str, Any]) -> Dict[str, EWMAResult]:
        """
        Updates all sensor detectors for the station with the latest telemetry values.

        Returns:
            Dictionary mapping metric name to EWMAResult.
        """
        results: Dict[str, EWMAResult] = {}
        for metric_name, val in telemetry.items():
            if val is None:
                continue
            try:
                numeric_val = float(val)
            except (ValueError, TypeError):
                continue

            if metric_name not in self.detectors:
                self.detectors[metric_name] = EWMADetector(
                    alpha=self.alpha,
                    target_mean=numeric_val,
                    std=1.0,
                    threshold=self.threshold,
                )

            results[metric_name] = self.detectors[metric_name].update(numeric_val)

        return results
