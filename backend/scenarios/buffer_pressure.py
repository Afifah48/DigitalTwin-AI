from typing import Dict, Any, Optional
import numpy as np
from .base import Scenario, ScenarioType, ScenarioSeverity
from ..simulation.engine import FactoryEngine
from ..models.enums import StationId, BufferId


class BufferPressureScenario(Scenario):
    """
    Scenario D: Buffer Pressure.
    Controls downstream pacing so upstream buffer progressively accumulates inventory:
    0/5 -> 1/5 -> 2/5 -> 3/5 -> 4/5 -> 5/5, training the model on queue buildup dynamics.
    """

    def __init__(
        self,
        target_buffer: BufferId = BufferId.B23,
        severity: ScenarioSeverity = ScenarioSeverity.MEDIUM,
        start_time: float = 900.0,
        duration: float = 1800.0,
        rng: Optional[np.random.Generator] = None,
    ):
        super().__init__(
            scenario_type=ScenarioType.BUFFER_PRESSURE,
            severity=severity,
            rng=rng,
        )
        self.target_buffer = target_buffer
        self.start_time = start_time
        self.duration = duration

        # Buffer B12 -> downstream S2; B23 -> S3; B34 -> S4; B45 -> S5; B56 -> S6
        buffer_to_downstream = {
            BufferId.B12: StationId.S2,
            BufferId.B23: StationId.S3,
            BufferId.B34: StationId.S4,
            BufferId.B45: StationId.S5,
            BufferId.B56: StationId.S6,
        }
        self.downstream_station_id = buffer_to_downstream[target_buffer]

    def apply(self, engine: FactoryEngine):
        station = engine.stations.get(self.downstream_station_id)
        if not station:
            return

        base_nominal = float(station.config.baseline_cycle_time)
        start_t = self.start_time
        end_t = self.start_time + self.duration

        # Slow down downstream station slightly above takt time to cause steady queue build
        if self.severity == ScenarioSeverity.LOW:
            extra_time = 8.0   # builds 1-2 vehicles in buffer
        elif self.severity == ScenarioSeverity.MEDIUM:
            extra_time = 18.0  # builds 3-4 vehicles in buffer
        else:
            extra_time = 32.0  # builds to full 5/5 capacity

        def dynamic_cycle_time(t: float) -> float:
            if start_t <= t <= end_t:
                return base_nominal + extra_time
            return base_nominal

        station.dynamic_baseline_cycle_time = dynamic_cycle_time

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "scenario_type": self.scenario_type.value,
            "severity": self.severity.value,
            "target_buffer": self.target_buffer.value,
            "affected_station": self.downstream_station_id.value,
            "start_time": round(self.start_time, 1),
            "end_time": round(self.start_time + self.duration, 1),
            "description": f"Controlled queue accumulation at buffer {self.target_buffer.value} pacing {self.downstream_station_id.value}.",
        }
