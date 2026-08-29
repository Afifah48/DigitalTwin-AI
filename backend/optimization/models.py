from typing import List, Optional, Dict
from pydantic import BaseModel

from ..models.enums import StationId
from ..counterfactual.models import CounterfactualAction, CounterfactualResult


class InterventionConstraint(BaseModel):
    """
    Defines limits on valid interventions to ensure operational realism.
    """
    max_budget: float = float('inf')
    max_cycle_time_reduction: float = 20.0  # seconds
    max_buffer_expansion: int = 5  # units
    max_downtime_reduction: float = 0.05  # percentage points
    prohibited_stations: List[StationId] = []


class OptimizationObjective(BaseModel):
    """
    Configurable weights for the multi-objective optimization function.
    """
    risk_reduction_weight: float = 100.0
    throughput_weight: float = 500.0
    queue_weight: float = 100.0
    cost_weight: float = 0.5
    disruption_weight: float = 5.0


class RecommendedIntervention(BaseModel):
    """
    Wrapper for a CounterfactualAction that includes optimization scoring.
    """
    action: CounterfactualAction
    score: float
    simulated_result: CounterfactualResult
    justification: str


class OptimizationResult(BaseModel):
    """
    The final output of Phase 9 representing the best intervention found.
    """
    objective: OptimizationObjective
    best_intervention: Optional[RecommendedIntervention]
    alternative_candidates: List[RecommendedIntervention]
    rejected_count: int
    computation_time_ms: float
