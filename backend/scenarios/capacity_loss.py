from typing import Dict, Any, Optional
import numpy as np
from .base import Scenario, ScenarioType, ScenarioSeverity
from ..simulation.engine import FactoryEngine
from ..models.enums import StationId


class DownstreamCapacityLossScenario(Scenario):
    """
    Scenario F: Downstream Capacity Loss.
    Reduces processing rate at downstream stations (S5 or S6), creating progressive
    upstream queue formation and backpressure blocking.
    """

    def __init__(
        self,
        target_station: StationId = StationId.S5,
        severity: ScenarioSeverity = ScenarioSeverity.MEDIUM,
        start_time: float = 800.0,
        duration: float = 2000.0,
        rng: Optional[np.random.Generator] = None,
    ):
        super().__init__(
            scenario_type=ScenarioType.DOWNSTREAM_CAPACITY_LOSS,
            severity=severity,
            rng=rng,
        )
        self.target_station = target_station
        self.start_time = start_time
        self.duration = duration

        if severity == ScenarioSeverity.LOW:
            self.capacity_slowdown = 12.0
        elif severity == ScenarioSeverity.MEDIUM:
            self.capacity_slowdown = 25.0
        else:
            self.capacity_slowdown = 45.0

    def apply(self, engine: FactoryEngine):
        station = engine.stations.get(self.target_station)
        if not station:
            return

        base_nominal = float(station.config.baseline_cycle_time)
        start_t = self.start_time
        end_t = self.start_time + self.duration
        slowdown = self.capacity_slowdown

        def dynamic_cycle_time(t: float) -> float:
            if start_t <= t <= end_t:
                return base_nominal + slowdown
            return base_nominal

        station.dynamic_baseline_cycle_time = dynamic_cycle_time

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "scenario_type": self.scenario_type.value,
            "severity": self.severity.value,
            "affected_station": self.target_station.value,
            "start_time": round(self.start_time, 1),
            "end_time": round(self.start_time + self.duration, 1),
            "capacity_slowdown": self.capacity_slowdown,
            "description": f"Downstream capacity reduction at station {self.target_station.value} (+{self.capacity_slowdown}s cycle time).",
        }
