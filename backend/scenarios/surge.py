from typing import Dict, Any, Optional
import numpy as np
from .base import Scenario, ScenarioType, ScenarioSeverity
from ..simulation.engine import FactoryEngine


class UpstreamSurgeScenario(Scenario):
    """
    Scenario E: Upstream Surge.
    Increases upstream vehicle body arrival rate (decreases arrival interval from 54s down to 35s),
    creating queue accumulation in input feeder and upstream buffer backpressure.
    """

    def __init__(
        self,
        severity: ScenarioSeverity = ScenarioSeverity.MEDIUM,
        start_time: float = 600.0,
        duration: float = 1800.0,
        rng: Optional[np.random.Generator] = None,
    ):
        super().__init__(
            scenario_type=ScenarioType.UPSTREAM_SURGE,
            severity=severity,
            rng=rng,
        )
        self.start_time = start_time
        self.duration = duration

        if severity == ScenarioSeverity.LOW:
            self.surge_arrival_interval = 46.0  # slight surge
        elif severity == ScenarioSeverity.MEDIUM:
            self.surge_arrival_interval = 38.0  # moderate surge
        else:
            self.surge_arrival_interval = 28.0  # aggressive inflow surge

    def apply(self, engine: FactoryEngine):
        nominal_interval = float(engine.config.input_arrival_interval)
        surge_interval = self.surge_arrival_interval
        start_t = self.start_time
        end_t = self.start_time + self.duration

        def dynamic_interval(t: float) -> float:
            if start_t <= t <= end_t:
                return surge_interval
            return nominal_interval

        engine.generator.dynamic_arrival_interval = dynamic_interval

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "scenario_type": self.scenario_type.value,
            "severity": self.severity.value,
            "affected_station": "FEEDER",
            "start_time": round(self.start_time, 1),
            "end_time": round(self.start_time + self.duration, 1),
            "surge_arrival_interval": self.surge_arrival_interval,
            "description": f"Upstream body supply surge (arrival interval reduced to {self.surge_arrival_interval}s).",
        }
