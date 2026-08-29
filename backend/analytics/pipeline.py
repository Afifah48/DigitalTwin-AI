"""
Main Factory Analytics Pipeline Module.

Coordinates all sub-modules (baseline, deviation, ewma, cusum, buffer, health, confidence)
to execute end-to-end telemetry analysis and return unified FactoryAnalytics snapshots.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Union

from backend.analytics.baseline import (
    DEFAULT_METRICS,
    DEFAULT_STATIONS,
    FactoryBaseline,
    calculate_baseline,
)
from backend.analytics.buffer import (
    BufferAnalytics,
    BufferTracker,
    StationFlowAnalytics,
    calculate_blocking,
    calculate_buffer_pressure,
    calculate_starvation,
)
from backend.analytics.confidence import (
    SensorConfidenceResult,
    calculate_sensor_confidence,
)
from backend.analytics.cusum import (
    CUSUMResult,
    StationCUSUMTracker,
)
from backend.analytics.deviation import (
    StationDeviation,
    calculate_deviation_score,
)
from backend.analytics.ewma import (
    EWMAResult,
    StationEWMATracker,
)
from backend.analytics.health import (
    FactoryHealth,
    StationHealth,
    calculate_factory_health,
    calculate_station_health,
)


@dataclass
class StationAnalytics:
    """Consolidated analytics results for a single station."""
    station_id: str
    state: str
    metrics: Dict[str, float]
    deviation: StationDeviation
    ewma: Dict[str, EWMAResult]
    cusum: Dict[str, CUSUMResult]
    flow: StationFlowAnalytics
    health: StationHealth
    confidence: SensorConfidenceResult

    def to_dict(self) -> Dict[str, Any]:
        return {
            "station_id": self.station_id,
            "state": self.state,
            "metrics": self.metrics,
            "deviation": self.deviation.to_dict(),
            "ewma": {k: v.to_dict() for k, v in self.ewma.items()},
            "cusum": {k: v.to_dict() for k, v in self.cusum.items()},
            "flow": self.flow.to_dict(),
            "health": self.health.to_dict(),
            "confidence": self.confidence.to_dict(),
        }


@dataclass
class FactoryAnalytics:
    """Comprehensive line-wide factory analytics snapshot."""
    factory_health: FactoryHealth
    stations: List[StationAnalytics]
    buffers: List[BufferAnalytics]
    highest_deviation_station: Optional[str] = None
    highest_buffer_pressure: Optional[str] = None
    highest_blocking_risk: Optional[str] = None
    highest_starvation_risk: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    created_at_iso: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factory_health": self.factory_health.to_dict(),
            "stations": [s.to_dict() for s in self.stations],
            "buffers": [b.to_dict() for b in self.buffers],
            "highest_deviation_station": self.highest_deviation_station,
            "highest_buffer_pressure": self.highest_buffer_pressure,
            "highest_blocking_risk": self.highest_blocking_risk,
            "highest_starvation_risk": self.highest_starvation_risk,
            "timestamp": self.timestamp,
            "created_at_iso": self.created_at_iso,
            "summary": self.summary,
        }


@dataclass
class AnalyticsPipelineConfig:
    """Configuration settings for the analytics pipeline."""
    ewma_alpha: float = 0.20
    ewma_threshold: float = 3.0
    cusum_drift_ratio: float = 0.5
    cusum_threshold_ratio: float = 4.0
    anomaly_z_threshold: float = 2.5
    default_buffer_capacity: float = 10.0
    observation_window: float = 60.0
    max_staleness_seconds: float = 10.0
    station_metric_weights: Optional[Dict[str, float]] = None


class AnalyticsEngine:
    """
    Stateful analytics engine maintaining historical EWMA, CUSUM, and Buffer trackers.
    """

    def __init__(
        self,
        baseline: Optional[FactoryBaseline] = None,
        config: Optional[AnalyticsPipelineConfig] = None,
    ) -> None:
        self.config = config or AnalyticsPipelineConfig()
        self.baseline = baseline
        self.ewma_trackers: Dict[str, StationEWMATracker] = {}
        self.cusum_trackers: Dict[str, StationCUSUMTracker] = {}
        self.buffer_trackers: Dict[str, BufferTracker] = {}

    def set_baseline(self, baseline: FactoryBaseline) -> None:
        """Sets or updates reference baseline."""
        self.baseline = baseline
        # Configure existing trackers with new baseline stats
        for st_id, tracker in self.ewma_trackers.items():
            st_base = baseline.get_station(st_id)
            if st_base:
                tracker.configure_from_baseline(st_base.metrics)

        for st_id, tracker in self.cusum_trackers.items():
            st_base = baseline.get_station(st_id)
            if st_base:
                tracker.configure_from_baseline(st_base.metrics)

    def analyze(
        self,
        factory_state: Dict[str, Any],
        telemetry_history: Optional[List[Dict[str, Any]]] = None,
    ) -> FactoryAnalytics:
        """Runs the complete 12-step pipeline on current factory state."""
        return analyze_factory(
            factory_state=factory_state,
            telemetry_history=telemetry_history,
            baseline=self.baseline,
            ewma_trackers=self.ewma_trackers,
            cusum_trackers=self.cusum_trackers,
            buffer_trackers=self.buffer_trackers,
            config=self.config,
        )


def analyze_factory(
    factory_state: Dict[str, Any],
    telemetry_history: Optional[List[Dict[str, Any]]] = None,
    baseline: Optional[FactoryBaseline] = None,
    ewma_trackers: Optional[Dict[str, StationEWMATracker]] = None,
    cusum_trackers: Optional[Dict[str, StationCUSUMTracker]] = None,
    buffer_trackers: Optional[Dict[str, BufferTracker]] = None,
    config: Optional[AnalyticsPipelineConfig] = None,
) -> FactoryAnalytics:
    """
    Main entrypoint executing the 12-step analytics pipeline:

    1. Load baseline (uses provided baseline or computes from normal telemetry_history)
    2. Calculate deltas
    3. Calculate z-scores
    4. Calculate EWMA
    5. Calculate CUSUM
    6. Calculate buffer pressure
    7. Calculate blocking
    8. Calculate starvation
    9. Calculate station health
    10. Calculate sensor confidence
    11. Calculate factory health
    12. Return FactoryAnalytics

    Args:
        factory_state: Current state dictionary with stations, buffers, timestamp.
        telemetry_history: Optional list of past snapshots for baseline computation or context.
        baseline: Pre-computed FactoryBaseline object.
        ewma_trackers: Optional dict of station EWMA trackers for stateful smoothing.
        cusum_trackers: Optional dict of station CUSUM trackers for stateful shift detection.
        buffer_trackers: Optional dict of buffer trackers.
        config: Pipeline configuration parameters.

    Returns:
        FactoryAnalytics containing complete station and factory health.
    """
    cfg = config or AnalyticsPipelineConfig()
    current_time = float(factory_state.get("timestamp", time.time()))

    # Step 1: Baseline resolution
    active_baseline = baseline
    if active_baseline is None:
        if telemetry_history:
            active_baseline = calculate_baseline(telemetry_history)
        else:
            # Create a dynamic fallback baseline based on current state
            active_baseline = calculate_baseline([factory_state])

    # Extract station and buffer state dictionaries
    raw_stations: Dict[str, Any] = factory_state.get("stations", {})
    raw_buffers: Dict[str, Any] = factory_state.get("buffers", {})
    obs_window = float(factory_state.get("observation_window", cfg.observation_window))

    # Initialize tracker maps if not provided
    ewma_map = ewma_trackers if ewma_trackers is not None else {}
    cusum_map = cusum_trackers if cusum_trackers is not None else {}
    buf_map = buffer_trackers if buffer_trackers is not None else {}

    station_analytics_list: List[StationAnalytics] = []
    buffer_analytics_list: List[BufferAnalytics] = []
    buffer_pressure_map: Dict[str, float] = {}

    highest_deviation_station: Optional[str] = None
    max_deviation_score = -1.0

    highest_buffer_pressure: Optional[str] = None
    max_buf_pressure = -1.0

    highest_blocking_risk: Optional[str] = None
    max_blocking_rate = -1.0

    highest_starvation_risk: Optional[str] = None
    max_starvation_rate = -1.0

    # Process Buffers (Step 6: Calculate Buffer Pressure & Dynamics)
    for buf_key, buf_data in raw_buffers.items():
        if isinstance(buf_data, dict):
            buf_id = str(buf_data.get("buffer_id", buf_key))
            occupancy = float(buf_data.get("occupancy", 0.0))
            capacity = float(buf_data.get("capacity", cfg.default_buffer_capacity))
            upstream = buf_data.get("upstream_station") or buf_data.get("upstream")
            downstream = buf_data.get("downstream_station") or buf_data.get("downstream")
        else:
            buf_id = str(buf_key)
            occupancy = float(buf_data)
            capacity = cfg.default_buffer_capacity
            upstream, downstream = None, None

        if buf_id not in buf_map:
            buf_map[buf_id] = BufferTracker(
                buffer_id=buf_id,
                capacity=capacity,
                upstream_station=upstream,
                downstream_station=downstream,
            )

        buf_analytics = buf_map[buf_id].update(occupancy)
        buffer_analytics_list.append(buf_analytics)
        buffer_pressure_map[buf_id] = buf_analytics.pressure

        if buf_analytics.pressure > max_buf_pressure:
            max_buf_pressure = buf_analytics.pressure
            highest_buffer_pressure = buf_id

    # If stations dictionary is empty, fall back to default station IDs
    target_station_ids = list(raw_stations.keys()) if raw_stations else list(DEFAULT_STATIONS)

    # Process Stations (Steps 2 to 10)
    for st_id in sorted(target_station_ids):
        st_data = raw_stations.get(st_id, {})
        if not isinstance(st_data, dict):
            st_data = {}

        machine_state = str(st_data.get("state", st_data.get("status", "RUNNING")))

        # Extract numeric sensor telemetry
        numeric_metrics: Dict[str, float] = {}
        for m in DEFAULT_METRICS:
            if m in st_data and st_data[m] is not None:
                try:
                    numeric_metrics[m] = float(st_data[m])
                except (ValueError, TypeError):
                    pass

        # Also capture any other custom metrics
        for k, v in st_data.items():
            if k not in DEFAULT_METRICS and k not in ("state", "status", "blocked_time", "starved_time", "timestamp"):
                if isinstance(v, (int, float)):
                    numeric_metrics[k] = float(v)

        st_baseline = active_baseline.get_station(st_id) if active_baseline else None

        # Step 2 & 3: Calculate deltas, z-scores, normalized deviation scores
        deviation = calculate_deviation_score(
            observed_metrics=numeric_metrics,
            station_baseline=st_baseline,
            weights=cfg.station_metric_weights,
            anomaly_z_threshold=cfg.anomaly_z_threshold,
        )

        if deviation.composite_deviation > max_deviation_score:
            max_deviation_score = deviation.composite_deviation
            highest_deviation_station = st_id

        # Step 4: Calculate EWMA
        if st_id not in ewma_map:
            ewma_map[st_id] = StationEWMATracker(
                station_id=st_id,
                alpha=cfg.ewma_alpha,
                threshold=cfg.ewma_threshold,
                baseline_metrics=st_baseline.metrics if st_baseline else None,
            )
        ewma_results = ewma_map[st_id].update_station(numeric_metrics)

        # Step 5: Calculate CUSUM
        if st_id not in cusum_map:
            cusum_map[st_id] = StationCUSUMTracker(
                station_id=st_id,
                drift_sigma_ratio=cfg.cusum_drift_ratio,
                threshold_sigma_ratio=cfg.cusum_threshold_ratio,
                baseline_metrics=st_baseline.metrics if st_baseline else None,
            )
        cusum_results = cusum_map[st_id].update_station(numeric_metrics)

        # Step 7: Calculate blocking
        blocked_time = float(st_data.get("blocked_time", 0.0))
        blocking_rate = calculate_blocking(blocked_time, obs_window)
        if blocking_rate > max_blocking_rate:
            max_blocking_rate = blocking_rate
            highest_blocking_risk = st_id

        # Step 8: Calculate starvation
        starved_time = float(st_data.get("starved_time", 0.0))
        starvation_rate = calculate_starvation(starved_time, obs_window)
        if starvation_rate > max_starvation_rate:
            max_starvation_rate = starvation_rate
            highest_starvation_risk = st_id

        flow_analytics = StationFlowAnalytics(
            station_id=st_id,
            blocked_time=blocked_time,
            starved_time=starved_time,
            observation_window=obs_window,
            blocking_rate=round(blocking_rate, 4),
            starvation_rate=round(starvation_rate, 4),
            is_blocked=blocking_rate > 0.30 or machine_state == "BLOCKED",
            is_starved=starvation_rate > 0.30 or machine_state == "STARVED",
        )

        # Step 10: Calculate sensor confidence
        data_timestamp = float(st_data.get("timestamp", current_time))
        age_seconds = max(0.0, current_time - data_timestamp)
        confidence = calculate_sensor_confidence(
            expected_sensors=DEFAULT_METRICS,
            reporting_telemetry=numeric_metrics,
            data_age_seconds=age_seconds,
            max_staleness_seconds=cfg.max_staleness_seconds,
        )

        # Immediate connected buffer pressure (if known)
        connected_buf_pressure = 0.0
        for b in buffer_analytics_list:
            if b.upstream_station == st_id or b.downstream_station == st_id:
                connected_buf_pressure = max(connected_buf_pressure, b.pressure)

        # Step 9: Calculate station health
        station_health = calculate_station_health(
            station_id=st_id,
            deviation_score=deviation.composite_deviation,
            buffer_pressure=connected_buf_pressure,
            blocking_rate=blocking_rate,
            starvation_rate=starvation_rate,
            machine_state=machine_state,
            telemetry_confidence=confidence.sensor_confidence,
        )

        station_analytics_list.append(
            StationAnalytics(
                station_id=st_id,
                state=machine_state,
                metrics=numeric_metrics,
                deviation=deviation,
                ewma=ewma_results,
                cusum=cusum_results,
                flow=flow_analytics,
                health=station_health,
                confidence=confidence,
            )
        )

    # Step 11: Calculate Factory Health
    factory_health = calculate_factory_health(
        station_healths=[s.health for s in station_analytics_list],
        buffer_pressures=buffer_pressure_map,
    )

    # Step 12: Assemble & Return FactoryAnalytics
    summary = {
        "total_stations": len(station_analytics_list),
        "total_buffers": len(buffer_analytics_list),
        "healthy_stations_count": sum(1 for s in station_analytics_list if s.health.is_healthy),
        "anomalous_stations_count": sum(1 for s in station_analytics_list if len(s.deviation.anomalous_metrics) > 0),
        "active_alarms_count": len(factory_health.active_alarms),
    }

    return FactoryAnalytics(
        factory_health=factory_health,
        stations=station_analytics_list,
        buffers=buffer_analytics_list,
        highest_deviation_station=highest_deviation_station if max_deviation_score > 0.1 else None,
        highest_buffer_pressure=highest_buffer_pressure if max_buf_pressure > 0.0 else None,
        highest_blocking_risk=highest_blocking_risk if max_blocking_rate > 0.05 else None,
        highest_starvation_risk=highest_starvation_risk if max_starvation_rate > 0.05 else None,
        timestamp=current_time,
        summary=summary,
    )
