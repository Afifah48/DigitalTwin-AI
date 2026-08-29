from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
import numpy as np
from ..simulation.engine import FactoryEngine
from ..models.enums import StationId, BufferId


class ScenarioType(str, Enum):
    NORMAL_OPERATION = "NORMAL_OPERATION"
    GRADUAL_STATION_DEGRADATION = "GRADUAL_STATION_DEGRADATION"
    SUDDEN_MACHINE_FAILURE = "SUDDEN_MACHINE_FAILURE"
    BUFFER_PRESSURE = "BUFFER_PRESSURE"
    UPSTREAM_SURGE = "UPSTREAM_SURGE"
    DOWNSTREAM_CAPACITY_LOSS = "DOWNSTREAM_CAPACITY_LOSS"
    QUALITY_DEGRADATION = "QUALITY_DEGRADATION"
    SENSOR_MISSINGNESS = "SENSOR_MISSINGNESS"
    CONSTRAINT_MIGRATION = "CONSTRAINT_MIGRATION"
    COMPOSITE_SCENARIO = "COMPOSITE_SCENARIO"


class ScenarioSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Scenario(ABC):
    """
    Abstract Base Class for factory digital twin disturbance and operating scenarios.
    Modifies parameters, curves, and sensor channels without duplicating factory DES physics.
    """

    def __init__(
        self,
        scenario_type: ScenarioType,
        severity: ScenarioSeverity = ScenarioSeverity.MEDIUM,
        rng: Optional[np.random.Generator] = None,
    ):
        self.scenario_type = scenario_type
        self.severity = severity
        self.rng = rng if rng is not None else np.random.default_rng()

    @abstractmethod
    def apply(self, engine: FactoryEngine):
        """Applies dynamic parameter curves or configuration hooks to the simulation engine."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Returns structured metadata describing the scenario configuration for training records."""
        pass

    def get_sensor_mask(self, station_id: StationId, t: float) -> Dict[str, bool]:
        """
        Returns a mapping of sensor channel -> available (True/False) for missingness simulation.
        By default, all sensors are available (True).
        """
        return {}
