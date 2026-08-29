from typing import Dict, Any, Optional, List
from enum import Enum
import numpy as np
from .base import Scenario, ScenarioType, ScenarioSeverity
from ..simulation.engine import FactoryEngine
from ..models.enums import StationId


class MissingnessPattern(str, Enum):
    RANDOM = "RANDOM"
    BURST = "BURST"
    STATION_SPECIFIC = "STATION_SPECIFIC"
    SENSOR_SPECIFIC = "SENSOR_SPECIFIC"


class SensorMissingnessScenario(Scenario):
    """
    Scenario H: Sensor Telemetry Missingness.
    Simulates packet loss, hardware telemetry dropout, or burst disconnection.
    The physical factory continues to operate accurately in the background.
    """

    def __init__(
        self,
        target_station: Optional[StationId] = StationId.S5,
        target_sensor: Optional[str] = None,
        pattern: MissingnessPattern = MissingnessPattern.BURST,
        severity: ScenarioSeverity = ScenarioSeverity.MEDIUM,
        start_time: float = 900.0,
        duration: float = 1200.0,
        missing_rate: Optional[float] = None,
        rng: Optional[np.random.Generator] = None,
    ):
        super().__init__(
            scenario_type=ScenarioType.SENSOR_MISSINGNESS,
            severity=severity,
            rng=rng,
        )
        self.target_station = target_station
        self.target_sensor = target_sensor
        self.pattern = pattern
        self.start_time = start_time
        self.duration = duration

        if missing_rate is None:
            if severity == ScenarioSeverity.LOW:
                self.missing_rate = 0.15
            elif severity == ScenarioSeverity.MEDIUM:
                self.missing_rate = 0.40
            else:
                self.missing_rate = 0.85
        else:
            self.missing_rate = missing_rate

    def apply(self, engine: FactoryEngine):
        # Physical engine simulation remains intact
        pass

    def get_sensor_mask(self, station_id: StationId, t: float) -> Dict[str, bool]:
        """
        Determines whether sensor channels at given timestamp t and station are available or dropped.
        """
        channels = ["cycle_time", "temperature", "vibration", "motor_current", "current_variance"]
        mask = {ch: True for ch in channels}

        # Check if missingness window is active
        if self.pattern == MissingnessPattern.RANDOM:
            # Independent random dropout per channel
            if self.target_station is None or station_id == self.target_station:
                for ch in channels:
                    if self.target_sensor is None or ch == self.target_sensor:
                        if self.rng.random() < self.missing_rate:
                            mask[ch] = False

        elif self.pattern == MissingnessPattern.BURST:
            # Complete or heavy dropout during time window [start_time, start_time + duration]
            if self.start_time <= t <= self.start_time + self.duration:
                if self.target_station is None or station_id == self.target_station:
                    for ch in channels:
                        if self.target_sensor is None or ch == self.target_sensor:
                            if self.rng.random() < (0.95 if self.severity == ScenarioSeverity.HIGH else self.missing_rate):
                                mask[ch] = False

        elif self.pattern == MissingnessPattern.STATION_SPECIFIC:
            if station_id == self.target_station:
                for ch in channels:
                    if self.rng.random() < self.missing_rate:
                        mask[ch] = False

        elif self.pattern == MissingnessPattern.SENSOR_SPECIFIC:
            if self.target_sensor in mask:
                if self.target_station is None or station_id == self.target_station:
                    if self.rng.random() < self.missing_rate:
                        mask[self.target_sensor] = False

        return mask

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "scenario_type": self.scenario_type.value,
            "severity": self.severity.value,
            "affected_station": self.target_station.value if self.target_station else "ALL",
            "pattern": self.pattern.value,
            "target_sensor": self.target_sensor or "ALL",
            "start_time": round(self.start_time, 1),
            "end_time": round(self.start_time + self.duration, 1),
            "missing_rate": self.missing_rate,
            "description": f"Telemetry missingness ({self.pattern.value}) affecting {self.target_station.value if self.target_station else 'ALL'}.",
        }
