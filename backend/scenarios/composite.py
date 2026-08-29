from typing import List, Dict, Any, Optional
import numpy as np
from .base import Scenario, ScenarioType, ScenarioSeverity
from ..simulation.engine import FactoryEngine
from ..models.enums import StationId


class CompositeScenario(Scenario):
    """
    Scenario I: Composite Multi-Disturbance Scenario.
    Combines multiple sub-scenarios (e.g. S3 degradation + S5 sensor missingness + S2 minor stop).
    """

    def __init__(
        self,
        sub_scenarios: List[Scenario],
        severity: ScenarioSeverity = ScenarioSeverity.MEDIUM,
        rng: Optional[np.random.Generator] = None,
    ):
        super().__init__(
            scenario_type=ScenarioType.COMPOSITE_SCENARIO,
            severity=severity,
            rng=rng,
        )
        self.sub_scenarios = sub_scenarios

    def apply(self, engine: FactoryEngine):
        for sub in self.sub_scenarios:
            sub.apply(engine)

    def get_sensor_mask(self, station_id: StationId, t: float) -> Dict[str, bool]:
        combined_mask: Dict[str, bool] = {}
        for sub in self.sub_scenarios:
            mask = sub.get_sensor_mask(station_id, t)
            for ch, avail in mask.items():
                if ch not in combined_mask or not avail:
                    combined_mask[ch] = avail
        return combined_mask

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "scenario_type": self.scenario_type.value,
            "severity": self.severity.value,
            "sub_scenario_count": len(self.sub_scenarios),
            "sub_scenarios": [s.get_metadata() for s in self.sub_scenarios],
            "description": f"Composite scenario combining {len(self.sub_scenarios)} simultaneous disturbances.",
        }
