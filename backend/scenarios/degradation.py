from typing import Dict, Any, Optional
import numpy as np
from .base import Scenario, ScenarioType, ScenarioSeverity
from ..simulation.engine import FactoryEngine
from ..models.enums import StationId


class GradualDegradationScenario(Scenario):
    """
    Scenario B: Station gradually becomes less efficient over time.
    Supports any station (S1 to S6) with configurable onset time, drift rate, and severity.
    """

    def __init__(
        self,
        target_station: StationId = StationId.S3,
        severity: ScenarioSeverity = ScenarioSeverity.MEDIUM,
        start_time: float = 600.0,
        duration: float = 2400.0,
        degradation_rate: Optional[float] = None,
        max_degradation: Optional[float] = None,
        rng: Optional[np.random.Generator] = None,
    ):
        super().__init__(
            scenario_type=ScenarioType.GRADUAL_STATION_DEGRADATION,
            severity=severity,
            rng=rng,
        )
        self.target_station = target_station
        self.start_time = start_time
        self.duration = duration

        if max_degradation is None:
            if severity == ScenarioSeverity.LOW:
                self.max_degradation = float(self.rng.uniform(5.0, 9.0))
            elif severity == ScenarioSeverity.MEDIUM:
                self.max_degradation = float(self.rng.uniform(15.0, 25.0))
            else:
                self.max_degradation = float(self.rng.uniform(30.0, 48.0))
        else:
            self.max_degradation = max_degradation

        if degradation_rate is None:
            self.degradation_rate = self.max_degradation / max(300.0, self.duration * 0.7)
        else:
            self.degradation_rate = degradation_rate

    def apply(self, engine: FactoryEngine):
        station = engine.stations.get(self.target_station)
        if not station:
            return

        base_nominal = float(station.config.baseline_cycle_time)
        start_t = self.start_time
        end_t = self.start_time + self.duration
        rate = self.degradation_rate
        max_drift = self.max_degradation

        def dynamic_cycle_time(t: float) -> float:
            if t < start_t:
                return base_nominal
            elapsed = min(end_t - start_t, t - start_t)
            drift = min(max_drift, elapsed * rate)
            return base_nominal + drift

        def dynamic_vibration(t: float) -> float:
            if t < start_t:
                return 0.0
            elapsed = min(end_t - start_t, t - start_t)
            ratio = min(1.0, elapsed / max(1.0, end_t - start_t))
            return float(ratio * (2.5 if self.severity == ScenarioSeverity.HIGH else 1.2))

        def dynamic_current_variance(t: float) -> float:
            if t < start_t:
                return 0.0
            elapsed = min(end_t - start_t, t - start_t)
            ratio = min(1.0, elapsed / max(1.0, end_t - start_t))
            return float(ratio * (2.0 if self.severity == ScenarioSeverity.HIGH else 0.8))

        station.dynamic_baseline_cycle_time = dynamic_cycle_time
        station.dynamic_vibration_offset = dynamic_vibration
        station.dynamic_current_variance_offset = dynamic_current_variance

    def get_metadata(self) -> Dict[str, Any]:
        sc_val = self.scenario_type.value if hasattr(self.scenario_type, "value") else str(self.scenario_type)
        sev_val = self.severity.value if hasattr(self.severity, "value") else str(self.severity)
        st_val = self.target_station.value if hasattr(self.target_station, "value") else str(self.target_station)
        return {
            "scenario_type": sc_val,
            "severity": sev_val,
            "affected_station": st_val,
            "start_time": round(self.start_time, 1),
            "end_time": round(self.start_time + self.duration, 1),
            "degradation_rate": round(self.degradation_rate, 4),
            "max_degradation": round(self.max_degradation, 1),
            "description": f"Gradual cycle-time degradation at station {st_val} drifting by +{self.max_degradation:.1f}s.",
        }
