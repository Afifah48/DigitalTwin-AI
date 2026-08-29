import copy
from typing import Optional, Dict, Any

from ..config.factory_config import FactoryConfig
from ..models.enums import StationId, BufferId
from ..models.states import FactoryState
from ..twin.digital_twin import DigitalTwin
from ..bottleneck.pipeline import BottleneckPipeline
from .models import InterventionType, CounterfactualAction, CounterfactualResult

class CounterfactualSimulator:
    """
    Evaluates the impact of a given intervention by running a twin simulation
    of the baseline configuration and a counterfactual configuration side-by-side.
    """

    def __init__(
        self,
        base_config: FactoryConfig,
        pipeline: Optional[BottleneckPipeline] = None,
        simulation_duration: float = 3600.0,
        seed: int = 42,
    ):
        self.base_config = base_config
        self.pipeline = pipeline or BottleneckPipeline()
        self.simulation_duration = simulation_duration
        self.seed = seed

    def apply_action_to_config(
        self, config: FactoryConfig, action: CounterfactualAction
    ) -> FactoryConfig:
        """Creates a mutated deep copy of the config incorporating the action."""
        action.validate_target()
        new_config = copy.deepcopy(config)

        if action.action_type == InterventionType.CYCLE_TIME_REDUCTION:
            st = new_config.station_configs[action.target_station]
            st.baseline_cycle_time += action.magnitude
            # Prevent impossible cycle times
            st.baseline_cycle_time = max(st.baseline_cycle_time, st.min_cycle_time)
            action.description = f"Reduced cycle time by {abs(action.magnitude)}s at {action.target_station.value}"

        elif action.action_type == InterventionType.DOWNTIME_REDUCTION:
            st = new_config.station_configs[action.target_station]
            st.failure_probability += action.magnitude
            st.failure_probability = max(0.0, st.failure_probability)
            action.description = f"Reduced failure probability by {abs(action.magnitude)} at {action.target_station.value}"

        elif action.action_type == InterventionType.BUFFER_EXPANSION:
            buf = new_config.buffer_configs[action.target_buffer]
            buf.capacity += int(action.magnitude)
            buf.capacity = max(1, buf.capacity)
            action.description = f"Expanded buffer {action.target_buffer.value} by {int(action.magnitude)} slots"

        else:
            raise ValueError(f"Unsupported intervention type: {action.action_type}")

        return new_config

    def _extract_telemetry_for_pipeline(self, state: FactoryState) -> Dict[StationId, Dict[str, Any]]:
        telemetries = {}
        for st_id, st_state in state.stations.items():
            t = st_state.telemetry
            # The pipeline expects a dictionary for Phase 4 adaptation.
            # We map properties to dict values here.
            telemetries[st_id] = {
                "cycle_time": t.cycle_time,
                "utilization": t.utilization,
                "cycle_time_deviation": t.cycle_time - self.base_config.station_configs[st_id].baseline_cycle_time,
                "vibration": 1.0,  # Mock values for sensors if needed by Phase 4 adapter
                "current_variance": 0.1,
                "machine_state": t.machine_state.value if hasattr(t.machine_state, "value") else t.machine_state,
                "queue_size": t.queue_length,
            }
        return telemetries
        
    def _extract_buffer_occupancies(self, state: FactoryState) -> Dict[BufferId, int]:
        return {b_id: b_state.current_occupancy for b_id, b_state in state.buffers.items()}

    def simulate(self, action: CounterfactualAction) -> CounterfactualResult:
        """Runs the baseline and counterfactual simulations and computes deltas."""
        # 1. Prepare configurations
        cf_config = self.apply_action_to_config(self.base_config, action)

        # 2. Run Baseline Simulation
        base_twin = DigitalTwin(config=self.base_config, seed=self.seed)
        base_state = base_twin.simulate(self.simulation_duration)

        # 3. Run Counterfactual Simulation
        cf_twin = DigitalTwin(config=cf_config, seed=self.seed)
        cf_state = cf_twin.simulate(self.simulation_duration)

        # 4. Evaluate Risks via Phase 5 Pipeline
        # Each evaluation MUST use a clean pipeline state — baseline and counterfactual
        # are independent snapshots and must not inherit each other's persistence state.
        self.pipeline.reset()
        base_analysis = self.pipeline.analyze_snapshot(
            timestamp=self.simulation_duration,
            station_telemetries=self._extract_telemetry_for_pipeline(base_state),
            buffer_occupancies=self._extract_buffer_occupancies(base_state),
        )

        self.pipeline.reset()
        cf_analysis = self.pipeline.analyze_snapshot(
            timestamp=self.simulation_duration,
            station_telemetries=self._extract_telemetry_for_pipeline(cf_state),
            buffer_occupancies=self._extract_buffer_occupancies(cf_state),
        )

        # 5. Compute Deltas
        base_tp = base_state.throughput_uph
        cf_tp = cf_state.throughput_uph
        tp_delta = cf_tp - base_tp

        base_primary_id = base_analysis.predicted_bottleneck_station
        cf_primary_id = cf_analysis.predicted_bottleneck_station

        # Use max station risk from ranking (always populated) rather than
        # predicted_bottleneck_risk which is 0.0 when no station crosses threshold.
        base_risk = max((s.risk_score for s in base_analysis.station_ranking), default=0.0)
        cf_risk = max((s.risk_score for s in cf_analysis.station_ranking), default=0.0)

        # If predicted_bottleneck_station is set, use its risk directly
        if base_analysis.predicted_bottleneck_risk > 0.0:
            base_risk = base_analysis.predicted_bottleneck_risk
        if cf_analysis.predicted_bottleneck_risk > 0.0:
            cf_risk = cf_analysis.predicted_bottleneck_risk

        risk_delta = cf_risk - base_risk
        
        # Calculate Queue and WIP metrics
        base_wip = sum(st.telemetry.wip for st in base_state.stations.values()) + sum(buf.current_occupancy for buf in base_state.buffers.values())
        cf_wip = sum(st.telemetry.wip for st in cf_state.stations.values()) + sum(buf.current_occupancy for buf in cf_state.buffers.values())
        wip_delta = cf_wip - base_wip
        
        base_queue = sum(st.telemetry.queue_length for st in base_state.stations.values())
        cf_queue = sum(st.telemetry.queue_length for st in cf_state.stations.values())
        queue_delta = cf_queue - base_queue

        # Extract confidence and affected stations from the analysis
        confidence = min(base_analysis.confidence, cf_analysis.confidence)
        
        base_affected = set()
        for s in base_analysis.station_ranking:
            if s.risk_score > 0:
                base_affected.update(s.affected_stations)
                
        cf_affected = set()
        for s in cf_analysis.station_ranking:
            if s.risk_score > 0:
                cf_affected.update(s.affected_stations)
                
        affected_stations = list(base_affected.union(cf_affected))

        return CounterfactualResult(
            action=action,
            baseline_throughput=base_tp,
            counterfactual_throughput=cf_tp,
            throughput_delta=tp_delta,
            baseline_risk=base_risk,
            counterfactual_risk=cf_risk,
            risk_delta=risk_delta,
            baseline_bottleneck_station=base_primary_id,
            counterfactual_bottleneck_station=cf_primary_id,
            baseline_total_wip=base_wip,
            counterfactual_total_wip=cf_wip,
            wip_delta=wip_delta,
            baseline_total_queue=base_queue,
            counterfactual_total_queue=cf_queue,
            queue_delta=queue_delta,
            confidence=confidence,
            affected_stations=affected_stations,
            baseline_analysis=base_analysis,
            counterfactual_analysis=cf_analysis,
            explanation=f"Evaluated {action.action_type.name} on {action.target_station or action.target_buffer}."
        )

