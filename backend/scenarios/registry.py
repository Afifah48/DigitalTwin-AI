from typing import Dict, Any, Optional, List
import numpy as np
from ..models.enums import StationId, BufferId
from .base import Scenario, ScenarioType, ScenarioSeverity
from .normal import NormalOperationScenario
from .degradation import GradualDegradationScenario
from .failure import SuddenFailureScenario
from .buffer_pressure import BufferPressureScenario
from .surge import UpstreamSurgeScenario
from .capacity_loss import DownstreamCapacityLossScenario
from .quality import QualityDegradationScenario
from .sensor import SensorMissingnessScenario, MissingnessPattern
from .migration import ConstraintMigrationScenario
from .composite import CompositeScenario


DEFAULT_SCENARIO_WEIGHTS: Dict[ScenarioType, float] = {
    ScenarioType.NORMAL_OPERATION: 0.20,
    ScenarioType.GRADUAL_STATION_DEGRADATION: 0.25,
    ScenarioType.SUDDEN_MACHINE_FAILURE: 0.10,
    ScenarioType.BUFFER_PRESSURE: 0.10,
    ScenarioType.UPSTREAM_SURGE: 0.08,
    ScenarioType.DOWNSTREAM_CAPACITY_LOSS: 0.07,
    ScenarioType.QUALITY_DEGRADATION: 0.08,
    ScenarioType.SENSOR_MISSINGNESS: 0.06,
    ScenarioType.CONSTRAINT_MIGRATION: 0.06,
}


class ScenarioRegistry:
    """
    Factory & Sampler for reproducible digital twin simulation episodes.
    """

    @staticmethod
    def sample_scenario(
        rng: Optional[np.random.Generator] = None,
        weights: Optional[Dict[ScenarioType, float]] = None,
    ) -> Scenario:
        rng = rng if rng is not None else np.random.default_rng()
        w_dict = weights or DEFAULT_SCENARIO_WEIGHTS

        sc_types = list(w_dict.keys())
        probs = np.array([w_dict[k] for k in sc_types], dtype=float)
        probs /= probs.sum()

        chosen_type_idx = rng.choice(len(sc_types), p=probs)
        chosen_type: ScenarioType = sc_types[chosen_type_idx]

        severities = [ScenarioSeverity.LOW, ScenarioSeverity.MEDIUM, ScenarioSeverity.HIGH]
        sev_idx = rng.choice(len(severities), p=[0.35, 0.45, 0.20])
        severity: ScenarioSeverity = severities[sev_idx]

        all_stations = [StationId.S1, StationId.S2, StationId.S3, StationId.S4, StationId.S5, StationId.S6]
        st_idx = rng.choice(len(all_stations))
        chosen_station = all_stations[st_idx]

        if chosen_type == ScenarioType.NORMAL_OPERATION:
            return NormalOperationScenario(severity=severity, rng=rng)

        elif chosen_type == ScenarioType.GRADUAL_STATION_DEGRADATION:
            start_t = float(rng.uniform(300.0, 900.0))
            duration = float(rng.uniform(1800.0, 3000.0))
            return GradualDegradationScenario(
                target_station=chosen_station,
                severity=severity,
                start_time=start_t,
                duration=duration,
                rng=rng,
            )

        elif chosen_type == ScenarioType.SUDDEN_MACHINE_FAILURE:
            fail_t = float(rng.uniform(600.0, 2400.0))
            return SuddenFailureScenario(
                target_station=chosen_station,
                severity=severity,
                failure_time=fail_t,
                rng=rng,
            )

        elif chosen_type == ScenarioType.BUFFER_PRESSURE:
            all_buffers = [BufferId.B12, BufferId.B23, BufferId.B34, BufferId.B45, BufferId.B56]
            buf_idx = rng.choice(len(all_buffers))
            chosen_buffer = all_buffers[buf_idx]
            start_t = float(rng.uniform(600.0, 1200.0))
            return BufferPressureScenario(
                target_buffer=chosen_buffer,
                severity=severity,
                start_time=start_t,
                rng=rng,
            )

        elif chosen_type == ScenarioType.UPSTREAM_SURGE:
            start_t = float(rng.uniform(600.0, 1200.0))
            return UpstreamSurgeScenario(
                severity=severity,
                start_time=start_t,
                rng=rng,
            )

        elif chosen_type == ScenarioType.DOWNSTREAM_CAPACITY_LOSS:
            downstream_options = [StationId.S4, StationId.S5, StationId.S6]
            down_idx = rng.choice(len(downstream_options))
            downstream_station = downstream_options[down_idx]
            start_t = float(rng.uniform(600.0, 1500.0))
            return DownstreamCapacityLossScenario(
                target_station=downstream_station,
                severity=severity,
                start_time=start_t,
                rng=rng,
            )

        elif chosen_type == ScenarioType.QUALITY_DEGRADATION:
            start_t = float(rng.uniform(300.0, 1000.0))
            return QualityDegradationScenario(
                target_station=chosen_station,
                severity=severity,
                start_time=start_t,
                rng=rng,
            )

        elif chosen_type == ScenarioType.SENSOR_MISSINGNESS:
            patterns = [MissingnessPattern.RANDOM, MissingnessPattern.BURST, MissingnessPattern.STATION_SPECIFIC]
            p_idx = rng.choice(len(patterns))
            pattern = patterns[p_idx]
            start_t = float(rng.uniform(600.0, 1800.0))
            return SensorMissingnessScenario(
                target_station=chosen_station if pattern != MissingnessPattern.RANDOM else None,
                pattern=pattern,
                severity=severity,
                start_time=start_t,
                rng=rng,
            )

        elif chosen_type == ScenarioType.CONSTRAINT_MIGRATION:
            st_indices = rng.choice(len(all_stations), size=2, replace=False)
            st1, st2 = all_stations[st_indices[0]], all_stations[st_indices[1]]
            start_t = float(rng.uniform(400.0, 800.0))
            mig_t = float(rng.uniform(1500.0, 2100.0))
            return ConstraintMigrationScenario(
                primary_station=st1,
                secondary_station=st2,
                severity=severity,
                start_time=start_t,
                migration_time=mig_t,
                rng=rng,
            )

        return NormalOperationScenario(severity=severity, rng=rng)
