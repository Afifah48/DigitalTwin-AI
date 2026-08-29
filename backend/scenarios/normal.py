from typing import Dict, Any, Optional
import numpy as np
from .base import Scenario, ScenarioType, ScenarioSeverity
from ..simulation.engine import FactoryEngine


class NormalOperationScenario(Scenario):
    """
    Scenario A: Healthy factory line with nominal takt time and standard stochastic variations.
    Serves as the clean negative baseline distribution.
    """

    def __init__(
        self,
        severity: ScenarioSeverity = ScenarioSeverity.LOW,
        rng: Optional[np.random.Generator] = None,
    ):
        super().__init__(
            scenario_type=ScenarioType.NORMAL_OPERATION,
            severity=severity,
            rng=rng,
        )

    def apply(self, engine: FactoryEngine):
        pass

    def get_metadata(self) -> Dict[str, Any]:
        sc_val = self.scenario_type.value if hasattr(self.scenario_type, "value") else str(self.scenario_type)
        sev_val = self.severity.value if hasattr(self.severity, "value") else str(self.severity)
        return {
            "scenario_type": sc_val,
            "severity": sev_val,
            "affected_station": None,
            "start_time": 0.0,
            "end_time": 3600.0,
            "description": "Nominal factory steady-state operation with standard process noise.",
        }
