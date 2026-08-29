"""
Phase 7 Decision & Operational Intelligence Schemas.

Defines strict, typed data contracts for factory decisions, root-cause hypotheses,
impact analysis, evidence attribution, and prioritized operational actions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FactoryStatus(str, Enum):
    NOMINAL = "NOMINAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionType(str, Enum):
    MONITOR = "MONITOR"
    INVESTIGATE_STATION = "INVESTIGATE_STATION"
    INSPECT_MACHINE = "INSPECT_MACHINE"
    QA_INSPECTION = "QA_INSPECTION"
    CHECK_UPSTREAM_FLOW = "CHECK_UPSTREAM_FLOW"
    CHECK_DOWNSTREAM_STARVATION = "CHECK_DOWNSTREAM_STARVATION"
    ESCALATE = "ESCALATE"


class PropagationDirection(str, Enum):
    NONE = "NONE"
    UPSTREAM_BLOCKING = "UPSTREAM_BLOCKING"
    DOWNSTREAM_STARVATION = "DOWNSTREAM_STARVATION"
    BIDIRECTIONAL = "BIDIRECTIONAL"


@dataclass
class DecisionEvidenceItem:
    """Individual piece of factual evidence backing a decision or root cause."""
    signal: str
    value: Any
    source: str         # "Phase 4 Anomaly", "Phase 5 Bottleneck", "Phase 6 Quality", "Telemetry"
    direction: str      # "ELEVATED", "DEGRADED", "SATURATED", "DEPLETED", "NORMAL"
    strength: float     # [0.0, 1.0]
    station_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal": self.signal,
            "value": round(float(self.value), 4) if isinstance(self.value, (float, int)) else self.value,
            "source": self.source,
            "direction": self.direction,
            "strength": round(float(self.strength), 4),
            "station_id": self.station_id,
        }


@dataclass
class RootCauseHypothesis:
    """Structured, interpretable explanation of an observed operational issue."""
    hypothesis_id: str
    category: str       # e.g., "MECHANICAL_DEGRADATION", "SUDDEN_TOOL_BREAKDOWN", "UPSTREAM_BLOCKING"
    description: str
    confidence: float   # [0.0, 1.0]
    station_id: Optional[str] = None
    supporting_evidence: List[DecisionEvidenceItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "category": self.category,
            "station_id": self.station_id,
            "description": self.description,
            "confidence": round(float(self.confidence), 4),
            "supporting_evidence": [e.to_dict() for e in self.supporting_evidence],
        }


@dataclass
class RecommendedActionItem:
    """Deterministic, prioritized operational guidance for plant operators."""
    action: str         # ActionType
    priority: str       # ActionPriority
    target: str         # e.g., "Station S3", "Buffer B2", "Vehicles [V018]"
    reason: str
    evidence_summary: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "priority": self.priority,
            "target": self.target,
            "reason": self.reason,
            "evidence_summary": self.evidence_summary,
        }


@dataclass
class ImpactSummary:
    """Consolidated assessment of station, flow, and vehicle consequences."""
    affected_stations: List[str] = field(default_factory=list)
    propagation_direction: str = PropagationDirection.NONE.value
    propagation_description: str = "Nominal line flow without disruption."
    upstream_blocked_stations: List[str] = field(default_factory=list)
    downstream_starved_stations: List[str] = field(default_factory=list)
    affected_vehicles: List[str] = field(default_factory=list)
    high_risk_vehicle_count: int = 0
    medium_risk_vehicle_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FactoryDecision:
    """Official Phase 7 Factory Decision & Operational Intelligence contract."""
    timestamp: float
    factory_status: str               # FactoryStatus value
    overall_risk: float               # [0.0, 1.0]
    primary_issue: Optional[str]
    affected_stations: List[str] = field(default_factory=list)
    affected_vehicles: List[str] = field(default_factory=list)
    root_causes: List[RootCauseHypothesis] = field(default_factory=list)
    impact: ImpactSummary = field(default_factory=ImpactSummary)
    recommended_actions: List[RecommendedActionItem] = field(default_factory=list)
    confidence: float = 1.0           # [0.0, 1.0]
    evidence: List[DecisionEvidenceItem] = field(default_factory=list)
    audit_trail: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.factory_status not in [s.value for s in FactoryStatus]:
            raise ValueError(f"Invalid factory_status: {self.factory_status}")
        if not (0.0 <= float(self.overall_risk) <= 1.0):
            raise ValueError(f"overall_risk must be in [0.0, 1.0], got {self.overall_risk}")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": round(float(self.timestamp), 2),
            "factory_status": self.factory_status,
            "overall_risk": round(float(self.overall_risk), 4),
            "primary_issue": self.primary_issue,
            "affected_stations": self.affected_stations,
            "affected_vehicles": self.affected_vehicles,
            "root_causes": [rc.to_dict() for rc in self.root_causes],
            "impact": self.impact.to_dict(),
            "recommended_actions": [ra.to_dict() for ra in self.recommended_actions],
            "confidence": round(float(self.confidence), 4),
            "evidence": [e.to_dict() for e in self.evidence],
            "audit_trail": self.audit_trail,
        }
