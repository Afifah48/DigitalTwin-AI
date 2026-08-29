from typing import Dict, Any, Optional
import numpy as np
from .base import Scenario, ScenarioType, ScenarioSeverity
from ..simulation.engine import FactoryEngine
from ..models.enums import StationId


class SuddenFailureScenario(Scenario):
    """
    Scenario C: Station unexpectedly suffers breakdown/downtime and later recovers.
    Models sudden unscheduled stop, repair MTTR duration, and return to service.
    """

    def __init__(
        self,
        target_station: StationId = StationId.S2,
        severity: ScenarioSeverity = ScenarioSeverity.MEDIUM,
        failure_time: float = 1200.0,
        downtime_duration: Optional[float] = None,
        rng: Optional[np.random.Generator] = None,
    ):
        super().__init__(
            scenario_type=ScenarioType.SUDDEN_MACHINE_FAILURE,
            severity=severity,
            rng=rng,
        )
        self.target_station = target_station
        self.failure_time = failure_time

        if downtime_duration is None:
            if severity == ScenarioSeverity.LOW:
                self.downtime_duration = float(self.rng.uniform(60.0, 120.0))
            elif severity == ScenarioSeverity.MEDIUM:
                self.downtime_duration = float(self.rng.uniform(180.0, 360.0))
            else:
                self.downtime_duration = float(self.rng.uniform(450.0, 720.0))
        else:
            self.downtime_duration = downtime_duration

    def apply(self, engine: FactoryEngine):
        station = engine.stations.get(self.target_station)
        if not station:
            return

        fail_t = self.failure_time
        repair_dur = self.downtime_duration

        def dynamic_fail_prob(t: float) -> float:
            if fail_t <= t <= fail_t + 120.0 and station.down_count == 0:
                return 1.0
            return 0.0

        station.config.repair_time = repair_dur
        station.config.repair_time_std = 5.0
        station.dynamic_failure_probability = dynamic_fail_prob

    def get_metadata(self) -> Dict[str, Any]:
        sc_val = self.scenario_type.value if hasattr(self.scenario_type, "value") else str(self.scenario_type)
        sev_val = self.severity.value if hasattr(self.severity, "value") else str(self.severity)
        st_val = self.target_station.value if hasattr(self.target_station, "value") else str(self.target_station)
        return {
            "scenario_type": sc_val,
            "severity": sev_val,
            "affected_station": st_val,
            "start_time": round(self.failure_time, 1),
            "end_time": round(self.failure_time + self.downtime_duration, 1),
            "downtime_duration": round(self.downtime_duration, 1),
            "description": f"Sudden machine failure at station {st_val} lasting {self.downtime_duration:.1f}s before recovery.",
        }
