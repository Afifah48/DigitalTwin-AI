import time
from typing import List

from ..models.enums import StationId, BufferId
from ..config.factory_config import FactoryConfig
from ..counterfactual.models import InterventionType, CounterfactualAction
from ..counterfactual.simulator import CounterfactualSimulator
from .models import (
    OptimizationObjective,
    InterventionConstraint,
    RecommendedIntervention,
    OptimizationResult,
)


class InterventionOptimizer:
    """
    Evaluates a set of potential interventions using the CounterfactualSimulator
    and ranks them according to a multi-objective cost function.
    """

    def __init__(
        self,
        base_config: FactoryConfig,
        objective: OptimizationObjective = None,
        constraint: InterventionConstraint = None,
        simulation_duration: float = 3600.0,
        seed: int = 42,
    ):
        self.base_config = base_config
        self.objective = objective or OptimizationObjective()
        self.constraint = constraint or InterventionConstraint()
        self.simulator = CounterfactualSimulator(
            base_config=base_config,
            simulation_duration=simulation_duration,
            seed=seed,
        )

    def _generate_candidates(self) -> List[CounterfactualAction]:
        """Generates a grid of feasible intervention candidates."""
        candidates = []
        
        station_ids = [
            StationId.S1, StationId.S2, StationId.S3, 
            StationId.S4, StationId.S5, StationId.S6
        ]
        
        buffer_ids = [
            BufferId.B12, BufferId.B23, BufferId.B34, 
            BufferId.B45, BufferId.B56
        ]

        # 1. Cycle Time Reductions
        for st_id in station_ids:
            if st_id in self.constraint.prohibited_stations:
                continue
            # Evaluate varying magnitudes
            for mag, cost in [(-2.0, 50.0), (-5.0, 100.0), (-10.0, 150.0), (-15.0, 200.0)]:
                if abs(mag) <= self.constraint.max_cycle_time_reduction:
                    candidates.append(CounterfactualAction(
                        target_station=st_id,
                        action_type=InterventionType.CYCLE_TIME_REDUCTION,
                        magnitude=mag,
                        cost=cost
                    ))
                    
        # 1.5 Downtime Reductions
        for st_id in station_ids:
            if st_id in self.constraint.prohibited_stations:
                continue
            for mag, cost in [(-0.01, 30.0), (-0.05, 100.0)]:
                if abs(mag) <= self.constraint.max_downtime_reduction:
                    candidates.append(CounterfactualAction(
                        target_station=st_id,
                        action_type=InterventionType.DOWNTIME_REDUCTION,
                        magnitude=mag,
                        cost=cost
                    ))

        # 2. Buffer Expansions
        for buf_id in buffer_ids:
            for mag, cost in [(2, 20.0), (5, 60.0)]:
                if mag <= self.constraint.max_buffer_expansion:
                    candidates.append(CounterfactualAction(
                        target_buffer=buf_id,
                        action_type=InterventionType.BUFFER_EXPANSION,
                        magnitude=mag,
                        cost=cost
                    ))

        return candidates

    def _calculate_score(self, result: CounterfactualSimulator, cost: float) -> float:
        """Calculates the fitness score based on the OptimizationObjective."""
        # Risk reduction is positive if risk decreased (baseline - counterfactual)
        risk_reduction = result.baseline_risk - result.counterfactual_risk
        
        # Throughput improvement is positive if throughput increased
        throughput_improvement = result.counterfactual_throughput - result.baseline_throughput
        norm_throughput = throughput_improvement / result.baseline_throughput if result.baseline_throughput > 0 else 0.0
        
        # Queue reduction is positive if queue length decreased
        queue_reduction = result.baseline_total_queue - result.counterfactual_total_queue
        norm_queue = queue_reduction / result.baseline_total_queue if result.baseline_total_queue > 0 else 0.0
        
        score = 0.0
        score += self.objective.risk_reduction_weight * risk_reduction
        score += self.objective.throughput_weight * norm_throughput
        score += self.objective.queue_weight * norm_queue
        score -= self.objective.cost_weight * cost
        
        # Penalty for migrating the bottleneck (disruption)
        if result.bottleneck_migrated:
            score -= self.objective.disruption_weight * 5.0  # arbitrary penalty scaling
            
        return score

    def optimize(self) -> OptimizationResult:
        """Runs the optimization loop over candidates and returns the ranked results."""
        start_time = time.time()
        candidates = self._generate_candidates()
        
        evaluated_candidates = []
        rejected_count = 0
        
        for action in candidates:
            if action.cost > self.constraint.max_budget:
                rejected_count += 1
                continue
                
            cf_result = self.simulator.simulate(action)
            score = self._calculate_score(cf_result, action.cost)
            
            justification = (
                f"Score: {score:.2f} | "
                f"Risk Delta: {cf_result.risk_delta:.4f} | "
                f"Throughput Delta: {cf_result.throughput_delta:.1f} UPH | "
                f"Queue Delta: {cf_result.queue_delta} units | "
                f"Cost: ${action.cost:.2f}"
            )
            
            if cf_result.bottleneck_migrated:
                justification += f" [Warning: Bottleneck shifted from {cf_result.baseline_bottleneck_station.value if cf_result.baseline_bottleneck_station else 'None'} to {cf_result.counterfactual_bottleneck_station.value if cf_result.counterfactual_bottleneck_station else 'None'}]"
            
            evaluated_candidates.append(
                RecommendedIntervention(
                    action=action,
                    score=score,
                    simulated_result=cf_result,
                    justification=justification
                )
            )

        # Sort descending by score
        evaluated_candidates.sort(key=lambda x: x.score, reverse=True)
        
        best = evaluated_candidates[0] if evaluated_candidates else None
        alternatives = evaluated_candidates[1:4] if len(evaluated_candidates) > 1 else []
        
        comp_time = (time.time() - start_time) * 1000.0

        return OptimizationResult(
            objective=self.objective,
            best_intervention=best,
            alternative_candidates=alternatives,
            rejected_count=rejected_count,
            computation_time_ms=comp_time
        )
