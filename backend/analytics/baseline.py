"""
Baseline calculation module for factory simulation telemetry.

Calculates statistical metrics (mean, std, min, max, count, p95) for all stations
(S1-S6) and sensor channels from NORMAL_OPERATION reference training data.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

# Default monitored metrics per station
DEFAULT_METRICS = (
    "cycle_time",
    "utilization",
    "queue",
    "WIP",
    "temperature",
    "vibration",
    "motor_current",
    "current_variance",
)

# Standard stations in the factory simulation
DEFAULT_STATIONS = ("S1", "S2", "S3", "S4", "S5", "S6")


@dataclass
class MetricBaseline:
    """Statistical baseline parameters for a single telemetry metric."""
    metric_name: str
    mean: float
    std: float
    min_val: float
    max_val: float
    count: int
    p95: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MetricBaseline:
        return cls(
            metric_name=str(data["metric_name"]),
            mean=float(data["mean"]),
            std=float(data["std"]),
            min_val=float(data.get("min_val", data["mean"])),
            max_val=float(data.get("max_val", data["mean"])),
            count=int(data.get("count", 1)),
            p95=float(data.get("p95", data["mean"])),
        )


@dataclass
class StationBaseline:
    """Collection of metric baselines for a specific station."""
    station_id: str
    metrics: Dict[str, MetricBaseline] = field(default_factory=dict)

    def get_metric(self, metric_name: str) -> Optional[MetricBaseline]:
        return self.metrics.get(metric_name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "station_id": self.station_id,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StationBaseline:
        station_id = data["station_id"]
        metrics = {
            k: MetricBaseline.from_dict(v) for k, v in data.get("metrics", {}).items()
        }
        return cls(station_id=station_id, metrics=metrics)


@dataclass
class FactoryBaseline:
    """Factory-wide baseline covering all stations and global metrics."""
    stations: Dict[str, StationBaseline] = field(default_factory=dict)
    sample_count: int = 0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_station(self, station_id: str) -> Optional[StationBaseline]:
        return self.stations.get(station_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stations": {k: v.to_dict() for k, v in self.stations.items()},
            "sample_count": self.sample_count,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FactoryBaseline:
        stations = {
            k: StationBaseline.from_dict(v)
            for k, v in data.get("stations", {}).items()
        }
        return cls(
            stations=stations,
            sample_count=int(data.get("sample_count", 0)),
            created_at=str(data.get("created_at", "")),
            metadata=dict(data.get("metadata", {})),
        )


def _compute_stats(values: Sequence[float], metric_name: str) -> MetricBaseline:
    """Computes mean, std, min, max, count, and 95th percentile for a series of values."""
    if not values:
        return MetricBaseline(
            metric_name=metric_name,
            mean=0.0,
            std=0.0,
            min_val=0.0,
            max_val=0.0,
            count=0,
            p95=0.0,
        )

    clean_vals = [float(v) for v in values if v is not None and not math.isnan(v)]
    n = len(clean_vals)
    if n == 0:
        return MetricBaseline(
            metric_name=metric_name,
            mean=0.0,
            std=0.0,
            min_val=0.0,
            max_val=0.0,
            count=0,
            p95=0.0,
        )

    mean_val = sum(clean_vals) / n
    if n > 1:
        variance = sum((x - mean_val) ** 2 for x in clean_vals) / (n - 1)
        std_val = math.sqrt(max(0.0, variance))
    else:
        std_val = 0.0

    sorted_vals = sorted(clean_vals)
    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]

    # Calculate 95th percentile index
    p95_idx = min(int(math.ceil(0.95 * n)) - 1, n - 1)
    p95_val = sorted_vals[max(0, p95_idx)]

    return MetricBaseline(
        metric_name=metric_name,
        mean=round(mean_val, 6),
        std=round(std_val, 6),
        min_val=round(min_val, 6),
        max_val=round(max_val, 6),
        count=n,
        p95=round(p95_val, 6),
    )


def calculate_baseline(
    normal_data: Union[
        List[Dict[str, Any]],
        Dict[str, List[Dict[str, Any]]],
        Dict[str, Any],
    ],
    target_metrics: Optional[Iterable[str]] = None,
    target_stations: Optional[Iterable[str]] = None,
) -> FactoryBaseline:
    """
    Calculates reference baseline statistics from normal operational data.

    Accepts multiple formats:
    1. List of time-stamped factory snapshots: [{'stations': {'S1': {'cycle_time': 12.0, ...}, ...}}, ...]
    2. Dict mapping station_id -> list of telemetry readings: {'S1': [{'cycle_time': 12.0, ...}, ...]}
    3. List of flattened station records: [{'station_id': 'S1', 'cycle_time': 12.0, ...}, ...]

    Args:
        normal_data: Historical telemetry collected during NORMAL_OPERATION.
        target_metrics: Iterable of metric names to baseline. Defaults to DEFAULT_METRICS.
        target_stations: Iterable of station IDs to baseline. Defaults to DEFAULT_STATIONS or discovered IDs.

    Returns:
        FactoryBaseline containing computed statistics per station and metric.
    """
    metrics_to_compute = set(target_metrics) if target_metrics else set(DEFAULT_METRICS)
    station_data: Dict[str, Dict[str, List[float]]] = {}

    total_samples = 0

    # Format 1 or 3: List of records / snapshots
    if isinstance(normal_data, list):
        total_samples = len(normal_data)
        for record in normal_data:
            if not isinstance(record, dict):
                continue

            # Format 1: Record contains 'stations' mapping
            if "stations" in record and isinstance(record["stations"], dict):
                for st_id, st_metrics in record["stations"].items():
                    if not isinstance(st_metrics, dict):
                        continue
                    if st_id not in station_data:
                        station_data[st_id] = {m: [] for m in metrics_to_compute}
                    for m in metrics_to_compute:
                        if m in st_metrics and st_metrics[m] is not None:
                            station_data[st_id].setdefault(m, []).append(float(st_metrics[m]))

            # Format 3: Record has 'station_id'
            elif "station_id" in record:
                st_id = str(record["station_id"])
                if st_id not in station_data:
                    station_data[st_id] = {m: [] for m in metrics_to_compute}
                for m in metrics_to_compute:
                    if m in record and record[m] is not None:
                        station_data[st_id].setdefault(m, []).append(float(record[m]))

    # Format 2: Dict mapping station_id -> list of records
    elif isinstance(normal_data, dict):
        # Check if it has 'stations' key
        if "stations" in normal_data and isinstance(normal_data["stations"], dict):
            return calculate_baseline(normal_data["stations"], target_metrics, target_stations)

        for st_id, records in normal_data.items():
            if not isinstance(records, list):
                continue
            total_samples = max(total_samples, len(records))
            if st_id not in station_data:
                station_data[st_id] = {m: [] for m in metrics_to_compute}
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                for m in metrics_to_compute:
                    if m in rec and rec[m] is not None:
                        station_data[st_id].setdefault(m, []).append(float(rec[m]))

    # Determine which stations to populate
    final_station_ids = set(station_data.keys())
    if target_stations:
        final_station_ids.update(target_stations)
    else:
        final_station_ids.update(DEFAULT_STATIONS)

    factory_baseline = FactoryBaseline(sample_count=total_samples)

    for st_id in sorted(final_station_ids):
        st_metrics_map: Dict[str, MetricBaseline] = {}
        st_readings = station_data.get(st_id, {})

        for metric_name in sorted(metrics_to_compute):
            vals = st_readings.get(metric_name, [])
            st_metrics_map[metric_name] = _compute_stats(vals, metric_name)

        factory_baseline.stations[st_id] = StationBaseline(
            station_id=st_id,
            metrics=st_metrics_map,
        )

    return factory_baseline


def save_baseline(baseline: FactoryBaseline, file_path: str) -> None:
    """Saves a FactoryBaseline object to a JSON file."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(baseline.to_dict(), f, indent=2)


def load_baseline(file_path: str) -> FactoryBaseline:
    """Loads a FactoryBaseline object from a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return FactoryBaseline.from_dict(data)
