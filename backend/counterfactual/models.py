from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from ..models.enums import StationId, BufferId
from ..bottleneck.models import FactoryBottleneckAnalysis


class InterventionType(Enum):
    """Types of actionable interventions supported by the simulator."""
    CYCLE_TIME_REDUCTION = "CYCLE_TIME_REDUCTION"
    BUFFER_EXPANSION = "BUFFER_EXPANSION"
    DOWNTIME_REDUCTION = "DOWNTIME_REDUCTION"


class CounterfactualAction(BaseModel):
    """
    Defines a generic factory intervention.
    Designed to be forward-compatible with future Phase 6/7 outputs.
    """
    target_station: Optional[StationId] = None
    target_buffer: Optional[BufferId] = None
    action_type: InterventionType
    magnitude: float  # E.g., -5.0 for cycle time, +2 for buffer capacity
    cost: float = 0.0
    description: str = ""

    def validate_target(self):
        """Ensures the action has a valid target."""
        if self.action_type == InterventionType.BUFFER_EXPANSION:
            if not self.target_buffer:
                raise ValueError("BUFFER_EXPANSION requires a target_buffer.")
        else:
            if not self.target_station:
                raise ValueError(f"{self.action_type.name} requires a target_station.")


class CounterfactualResult(BaseModel):
    """
    Exposes the calculated differences between baseline and counterfactual simulated runs.
    """
    action: CounterfactualAction
    
    # Raw throughput metrics
    baseline_throughput: float
    counterfactual_throughput: float
    throughput_delta: float
    
    # Bottleneck and Risk metrics derived from Phase 5 Pipeline
    baseline_risk: float
    counterfactual_risk: float
    risk_delta: float
    
    baseline_bottleneck_station: Optional[StationId]
    counterfactual_bottleneck_station: Optional[StationId]
    
    # Queue and Buffer metrics
    baseline_total_wip: int = 0
    counterfactual_total_wip: int = 0
    wip_delta: int = 0

    baseline_total_queue: int = 0
    counterfactual_total_queue: int = 0
    queue_delta: int = 0
    
    # Factory-wide state snapshots
    baseline_analysis: FactoryBottleneckAnalysis
    counterfactual_analysis: FactoryBottleneckAnalysis
    
    # Confidence and affected stations
    confidence: float = 1.0
    affected_stations: List[StationId] = []
    
    explanation: str = ""

    @property
    def bottleneck_migrated(self) -> bool:
        """Returns True if the primary bottleneck shifted to a different station."""
        return self.baseline_bottleneck_station != self.counterfactual_bottleneck_station
