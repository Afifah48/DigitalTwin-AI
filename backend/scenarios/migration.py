from typing import Dict, Any, Optional
import numpy as np
from .base import Scenario, ScenarioType, ScenarioSeverity
from ..simulation.engine import FactoryEngine
from ..models.enums import StationId


class ConstraintMigrationScenario(Scenario):
    """
    Scenario: Constraint Migration.
    Station A (e.g. S3) degrades initially, building backlog.
    When Station A recovers at t_migration, the accumulated inventory surges into Station B (e.g. S4),
    causing Station B to become the new emerging constraint.
    """

    def __init__(
        self,
        primary_station: StationId = StationId.S3,
        secondary_station: StationId = StationId.S4,
        severity: ScenarioSeverity = ScenarioSeverity.MEDIUM,
        start_time: float = 600.0,
        migration_time: float = 1800.0,
        end_time: float = 3300.0,
        rng: Optional[np.random.Generator] = None,
    ):
        super().__init__(
            scenario_type=ScenarioType.CONSTRAINT_MIGRATION,
            severity=severity,
            rng=rng,
        )
        self.primary_station = primary_station
        self.secondary_station = secondary_station
        self.start_time = start_time
        self.migration_time = migration_time
        self.end_time = end_time

        if severity == ScenarioSeverity.LOW:
            self.primary_drift = 15.0
            self.secondary_drift = 12.0
        elif severity == ScenarioSeverity.MEDIUM:
            self.primary_drift = 28.0
            self.secondary_drift = 22.0
        else:
            self.primary_drift = 45.0
            self.secondary_drift = 35.0

    def apply(self, engine: FactoryEngine):
        st1 = engine.stations.get(self.primary_station)
        st2 = engine.stations.get(self.secondary_station)
        if not st1 or not st2:
            return

        base1 = float(st1.config.baseline_cycle_time)
        base2 = float(st2.config.baseline_cycle_time)

        t_start = self.start_time
        t_mig = self.migration_time
        t_end = self.end_time
        drift1 = self.primary_drift
        drift2 = self.secondary_drift

        # Primary station degrades during [t_start, t_mig], then recovers
        def st1_cycle(t: float) -> float:
            if t_start <= t < t_mig:
                progress = min(1.0, (t - t_start) / max(1.0, (t_mig - t_start) * 0.6))
                return base1 + (drift1 * progress)
            return base1

        # Secondary station degrades after t_mig when surge hits
        def st2_cycle(t: float) -> float:
            if t_mig <= t <= t_end:
                progress = min(1.0, (t - t_mig) / max(1.0, (t_end - t_mig) * 0.5))
                return base2 + (drift2 * progress)
            return base2

        st1.dynamic_baseline_cycle_time = st1_cycle
        st2.dynamic_baseline_cycle_time = st2_cycle

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "scenario_type": self.scenario_type.value,
            "severity": self.severity.value,
            "primary_station": self.primary_station.value,
            "secondary_station": self.secondary_station.value,
            "start_time": round(self.start_time, 1),
            "migration_time": round(self.migration_time, 1),
            "end_time": round(self.end_time, 1),
            "primary_drift": self.primary_drift,
            "secondary_drift": self.secondary_drift,
            "description": f"Constraint migration from {self.primary_station.value} to {self.secondary_station.value} at t={self.migration_time:.0f}s.",
        }
