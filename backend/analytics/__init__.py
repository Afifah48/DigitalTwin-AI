"""
Factory Simulation Analytics Engine Package (Phase 3).

Exposes baseline computation, anomaly deviation, EWMA drift detection, CUSUM shift detection,
buffer/flow dynamics, multi-factor health scoring, sensor confidence assessment, and the unified
12-step pipeline.
"""

from backend.analytics.baseline import (
    DEFAULT_METRICS,
    DEFAULT_STATIONS,
    FactoryBaseline,
    MetricBaseline,
    StationBaseline,
    calculate_baseline,
    load_baseline,
    save_baseline,
)
from backend.analytics.buffer import (
    BufferAnalytics,
    BufferPressureLevel,
    BufferTracker,
    StationFlowAnalytics,
    calculate_blocking,
    calculate_buffer_pressure,
    calculate_starvation,
    get_pressure_level,
)
from backend.analytics.confidence import (
    SensorConfidenceResult,
    calculate_data_freshness,
    calculate_sensor_confidence,
)
from backend.analytics.cusum import (
    CUSUMDetector,
    CUSUMDirection,
    CUSUMResult,
    StationCUSUMTracker,
)
from backend.analytics.deviation import (
    MetricDeviation,
    StationDeviation,
    calculate_delta,
    calculate_deviation_score,
    calculate_z_score,
    normalize_z_to_deviation,
)
from backend.analytics.ewma import (
    EWMADetector,
    EWMAResult,
    StationEWMATracker,
)
from backend.analytics.health import (
    FactoryHealth,
    HealthLevel,
    MachineHealthBreakdown,
    StationHealth,
    calculate_factory_health,
    calculate_station_health,
    score_to_health_level,
)
from backend.analytics.pipeline import (
    AnalyticsEngine,
    AnalyticsPipelineConfig,
    FactoryAnalytics,
    StationAnalytics,
    analyze_factory,
)

__all__ = [
    # baseline
    "DEFAULT_METRICS",
    "DEFAULT_STATIONS",
    "MetricBaseline",
    "StationBaseline",
    "FactoryBaseline",
    "calculate_baseline",
    "save_baseline",
    "load_baseline",
    # deviation
    "MetricDeviation",
    "StationDeviation",
    "calculate_delta",
    "calculate_z_score",
    "normalize_z_to_deviation",
    "calculate_deviation_score",
    # ewma
    "EWMAResult",
    "EWMADetector",
    "StationEWMATracker",
    # cusum
    "CUSUMDirection",
    "CUSUMResult",
    "CUSUMDetector",
    "StationCUSUMTracker",
    # buffer
    "BufferPressureLevel",
    "BufferAnalytics",
    "StationFlowAnalytics",
    "BufferTracker",
    "calculate_buffer_pressure",
    "get_pressure_level",
    "calculate_blocking",
    "calculate_starvation",
    # health
    "HealthLevel",
    "MachineHealthBreakdown",
    "StationHealth",
    "FactoryHealth",
    "score_to_health_level",
    "calculate_station_health",
    "calculate_factory_health",
    # confidence
    "SensorConfidenceResult",
    "calculate_data_freshness",
    "calculate_sensor_confidence",
    # pipeline
    "StationAnalytics",
    "FactoryAnalytics",
    "AnalyticsPipelineConfig",
    "AnalyticsEngine",
    "analyze_factory",
]
