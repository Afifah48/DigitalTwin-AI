from typing import Dict, Any, Optional
import numpy as np
from .base import Scenario, ScenarioType, ScenarioSeverity
from ..simulation.engine import FactoryEngine
from ..models.enums import StationId


class QualityDegradationScenario(Scenario):
    """
    Scenario G: Quality Process Degradation.
    Introduces process anomalies (temperature drift, excessive spindle vibration, current variance spikes)
    that increase latent vehicle stress and defect risk without causing immediate line blockages.
    """

    def __init__(
        self,
        target_station: StationId = StationId.S3,
        severity: ScenarioSeverity = ScenarioSeverity.MEDIUM,
        start_time: float = 600.0,
        duration: float = 2400.0,
        rng: Optional[np.random.Generator] = None,
    ):
        super().__init__(
            scenario_type=ScenarioType.QUALITY_DEGRADATION,
            severity=severity,
            rng=rng,
        )
        self.target_station = target_station
        self.start_time = start_time
        self.duration = duration

        if severity == ScenarioSeverity.LOW:
            self.vib_boost = 1.8
            self.temp_boost = 6.0
            self.var_boost = 0.8
        elif severity == ScenarioSeverity.MEDIUM:
            self.vib_boost = 3.5
            self.temp_boost = 14.0
            self.var_boost = 2.2
        else:
            self.vib_boost = 6.0
            self.temp_boost = 24.0
            self.var_boost = 4.5

    def apply(self, engine: FactoryEngine):
        station = engine.stations.get(self.target_station)
        if not station:
            return

        start_t = self.start_time
        end_t = self.start_time + self.duration
        vb = self.vib_boost
        tb = self.temp_boost
        vab = self.var_boost

        def dynamic_vibration(t: float) -> float:
            if start_t <= t <= end_t:
                progress = min(1.0, (t - start_t) / max(1.0, (end_t - start_t) * 0.5))
                return float(vb * progress)
            return 0.0

        def dynamic_temperature(t: float) -> float:
            if start_t <= t <= end_t:
                progress = min(1.0, (t - start_t) / max(1.0, (end_t - start_t) * 0.5))
                return float(tb * progress)
            return 0.0

        def dynamic_current_variance(t: float) -> float:
            if start_t <= t <= end_t:
                progress = min(1.0, (t - start_t) / max(1.0, (end_t - start_t) * 0.5))
                return float(vab * progress)
            return 0.0

        station.dynamic_vibration_offset = dynamic_vibration
        station.dynamic_temperature_offset = dynamic_temperature
        station.dynamic_current_variance_offset = dynamic_current_variance

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "scenario_type": self.scenario_type.value,
            "severity": self.severity.value,
            "affected_station": self.target_station.value,
            "start_time": round(self.start_time, 1),
            "end_time": round(self.start_time + self.duration, 1),
            "vibration_boost": self.vib_boost,
            "temperature_boost": self.temp_boost,
            "current_variance_boost": self.var_boost,
            "description": f"Process quality instability at station {self.target_station.value} (elevated vibration, temperature, torque variance).",
        }
