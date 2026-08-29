from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from ..models.enums import StationId


class ReasonCode(str, Enum):
    CYCLE_TIME_DEGRADATION = "CYCLE_TIME_DEGRADATION"
    QUEUE_ACCUMULATION = "QUEUE_ACCUMULATION"
    BUFFER_SATURATION = "BUFFER_SATURATION"
    FLOW_IMBALANCE = "FLOW_IMBALANCE"
    MACHINE_DOWNTIME = "MACHINE_DOWNTIME"
    PHASE4_ANOMALY = "PHASE4_ANOMALY"
    UPSTREAM_BLOCKING = "UPSTREAM_BLOCKING"
    DOWNSTREAM_STARVATION = "DOWNSTREAM_STARVATION"


class BottleneckClass(str, Enum):
    NOMINAL = "NOMINAL"
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class PropagationDirection(str, Enum):
    NONE = "NONE"
    UPSTREAM_BLOCKING = "UPSTREAM_BLOCKING"
    DOWNSTREAM_STARVATION = "DOWNSTREAM_STARVATION"
    BIDIRECTIONAL = "BIDIRECTIONAL"


class AnomalyPrediction(BaseModel):
    """
    Phase 4 Anomaly Detection Output Contract.
    Frozen interface consumed by Phase 5 without touching Phase 4 model internals.
    """
    station_id: StationId
    timestamp: float
    anomaly_score: float = Field(default=0.0, description="Raw or normalized anomaly score [0.0, 1.0]")
    anomaly_probability: Optional[float] = Field(default=None, description="Calibrated probability if provided by Phase 4")
    severity: str = Field(default="LOW", description="Severity category: LOW, MEDIUM, HIGH, CRITICAL")
    detected: bool = Field(default=False, description="Binary threshold detection flag")
    lead_time_if_known: Optional[float] = Field(default=None, description="Estimated lead time in seconds")
    top_signals: List[str] = Field(default_factory=list, description="List of primary anomaly-contributing feature names")


class BottleneckEvidence(BaseModel):
    """
    Structured interpretable signal attribution for bottleneck risk reasoning.
    """
    signal: str = Field(..., description="Feature or metric name (e.g., cycle_time, queue_length)")
    value: float = Field(..., description="Observed raw or delta value")
    normalized_strength: float = Field(..., description="Normalized contribution strength [0.0, 1.0]")
    direction: str = Field(..., description="Direction: 'increasing', 'decreasing', 'critical', 'elevated'")
    source: str = Field(..., description="Source category: 'TELEMETRY', 'QUEUE', 'BUFFER', 'FLOW', 'ANOMALY', 'STATE'")


class StationBottleneckRisk(BaseModel):
    """
    Station-level comprehensive bottleneck assessment, persistence, and propagation metrics.
    """
    station_id: StationId
    timestamp: float
    risk_score: float = Field(..., description="Combined bottleneck risk score in [0.0, 1.0]")
    prediction: BottleneckClass = Field(..., description="Categorical risk classification")
    confidence: float = Field(..., description="Telemetry & evidence confidence score in [0.0, 1.0]")
    persistence_score: float = Field(default=0.0, description="Temporal persistence measure [0.0, 1.0]")
    anomaly_score: float = Field(default=0.0, description="Phase 4 anomaly score")
    anomaly_probability: Optional[float] = Field(default=None, description="Phase 4 calibrated anomaly probability")
    anomaly_detected: bool = Field(default=False, description="Phase 4 binary anomaly flag")
    reason_codes: List[str] = Field(default_factory=list, description="Categorical reason codes attributing risk")
    time_to_bottleneck_seconds: Optional[float] = Field(default=None, description="Estimated time in seconds until critical bottleneck onset")
    evidence: List[BottleneckEvidence] = Field(default_factory=list, description="Attributed diagnostic evidence")
    upstream_blocking_risk: float = Field(default=0.0, description="Risk of blocking upstream neighbor [0.0, 1.0]")
    downstream_starvation_risk: float = Field(default=0.0, description="Risk of starving downstream neighbor [0.0, 1.0]")
    propagation_score: float = Field(default=0.0, description="Overall spatial constraint propagation strength [0.0, 1.0]")
    affected_stations: List[StationId] = Field(default_factory=list, description="List of directly affected spatial neighbors")


class FactoryBottleneckAnalysis(BaseModel):
    """
    Factory-wide bottleneck analysis and ranking snapshot at timestamp t.
    """
    timestamp: float
    predicted_bottleneck_station: Optional[StationId] = Field(default=None, description="Highest-risk station or None if nominal")
    predicted_bottleneck_risk: float = Field(default=0.0, description="Risk score of the primary bottleneck station")
    bottleneck_dominance: float = Field(default=0.0, description="Dominance margin of top bottleneck over secondary constraints [0.0, 1.0]")
    active_bottlenecks: List[StationId] = Field(default_factory=list, description="All stations exceeding the bottleneck risk threshold")
    confidence: float = Field(default=1.0, description="System confidence in the primary prediction")
    estimated_time_to_bottleneck_seconds: Optional[float] = Field(default=None, description="Estimated time in seconds until primary bottleneck onset")
    station_ranking: List[StationBottleneckRisk] = Field(default_factory=list, description="Ordered ranking of S1-S6 from highest to lowest risk")
    propagation: Dict[str, Any] = Field(default_factory=dict, description="Spatial propagation summary details")
    constraint_migration: Optional[Dict[str, Any]] = Field(default=None, description="Details of recent bottleneck shift between stations if any")
    summary: str = Field(default="", description="Human-interpretable industrial reasoning diagnosis")

