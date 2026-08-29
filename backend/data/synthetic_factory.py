"""
Synthetic Factory Data Generator for Phase 4 ML Anomaly Detection.

Generates realistic, multi-run factory telemetry trajectories partitioned strictly
by simulation run IDs (Train, Validation, and 5 Multi-Scenario Test Runs).
"""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


class ScenarioType(str, Enum):
    NORMAL = "NORMAL"
    GRADUAL_S3_DEGRADATION = "GRADUAL_S3_DEGRADATION"
    SUDDEN_FAILURE = "SUDDEN_FAILURE"
    SENSOR_MISSINGNESS = "SENSOR_MISSINGNESS"
    OTHER_STATION_DISTURBANCE = "OTHER_STATION_DISTURBANCE"


@dataclass
class TelemetrySnapshot:
    """A single factory-wide telemetry snapshot at a specific point in time."""
    run_id: str
    step_index: int
    timestamp: float
    scenario: str
    stations: Dict[str, Dict[str, Any]]
    buffers: Dict[str, Dict[str, Any]]
    ground_truth_anomalies: Dict[str, bool] = field(default_factory=dict)
    ground_truth_failure_times: Dict[str, Optional[float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Nominal parameters per station (S1-S6)
NOMINAL_STATION_PARAMS: Dict[str, Dict[str, float]] = {
    "S1": {"cycle_time": 45.0, "temp": 60.0, "vib": 0.08, "curr": 4.5, "curr_var": 0.04, "util": 0.82},
    "S2": {"cycle_time": 48.0, "temp": 62.0, "vib": 0.09, "curr": 4.8, "curr_var": 0.05, "util": 0.84},
    "S3": {"cycle_time": 54.0, "temp": 65.0, "vib": 0.10, "curr": 5.2, "curr_var": 0.05, "util": 0.88},
    "S4": {"cycle_time": 50.0, "temp": 63.0, "vib": 0.09, "curr": 5.0, "curr_var": 0.05, "util": 0.85},
    "S5": {"cycle_time": 46.0, "temp": 61.0, "vib": 0.08, "curr": 4.6, "curr_var": 0.04, "util": 0.83},
    "S6": {"cycle_time": 44.0, "temp": 59.0, "vib": 0.07, "curr": 4.4, "curr_var": 0.04, "util": 0.80},
}


def simulate_factory_run(
    run_id: str,
    scenario: ScenarioType = ScenarioType.NORMAL,
    total_steps: int = 60,
    time_step_sec: float = 5.0,
    random_seed: Optional[int] = None,
) -> List[TelemetrySnapshot]:
    """
    Generates a full time-series factory simulation run.

    Args:
        run_id: Unique string identifier for this simulation run.
        scenario: ScenarioType governing operational behavior and faults.
        total_steps: Total observation steps in the trajectory.
        time_step_sec: Sampling interval (default 5.0 seconds).
        random_seed: Random seed for deterministic reproducibility.

    Returns:
        List of TelemetrySnapshot records.
    """
    rng = random.Random(random_seed)
    np_rng = np.random.RandomState(random_seed)

    snapshots: List[TelemetrySnapshot] = []
    base_time = 1700000000.0

    # Running buffer occupancies
    buffer_occupancies = {f"B{k}": 3.0 + rng.uniform(-0.5, 0.5) for k in range(1, 6)}
    buffer_capacities = {f"B{k}": 10.0 for k in range(1, 6)}

    # Target bottleneck / failure ground truth timing
    gt_failure_time: Optional[float] = None
    if scenario == ScenarioType.GRADUAL_S3_DEGRADATION:
        gt_failure_time = base_time + (45 * time_step_sec)
    elif scenario == ScenarioType.SUDDEN_FAILURE:
        gt_failure_time = base_time + (25 * time_step_sec)

    for step in range(total_steps):
        t = base_time + (step * time_step_sec)
        stations_data: Dict[str, Dict[str, Any]] = {}
        gt_anomalies: Dict[str, bool] = {}
        gt_failures: Dict[str, Optional[float]] = {}

        for st_id, base_p in NOMINAL_STATION_PARAMS.items():
            # Standard Gaussian operational noise
            cycle_time = max(10.0, base_p["cycle_time"] + np_rng.normal(0, 0.8))
            temperature = base_p["temp"] + np_rng.normal(0, 0.4)
            vibration = max(0.01, base_p["vib"] + np_rng.normal(0, 0.005))
            motor_current = max(0.5, base_p["curr"] + np_rng.normal(0, 0.1))
            current_variance = max(0.01, base_p["curr_var"] + np_rng.normal(0, 0.005))
            utilization = min(0.99, max(0.1, base_p["util"] + np_rng.normal(0, 0.01)))
            queue_length = max(0, int(round(2 + np_rng.normal(0, 0.6))))
            wip = max(1, int(round(2 + np_rng.normal(0, 0.5))))
            machine_state = "RUNNING"
            is_anomaly = False

            # SCENARIO 2: Gradual S3 Bearing & Thermal Degradation
            if scenario == ScenarioType.GRADUAL_S3_DEGRADATION and st_id == "S3":
                # Degradation starts at step 15, progressively worsens until bottleneck at step 45
                if step >= 15:
                    progress = (step - 15) / 30.0  # 0.0 at step 15 -> 1.0 at step 45
                    cycle_time += progress * 16.0  # 54 -> 70 sec
                    temperature += progress * 24.0  # 65 -> 89 °C
                    vibration += progress * 0.32    # 0.10 -> 0.42
                    motor_current += progress * 4.5 # 5.2 -> 9.7 A
                    current_variance += progress * 0.45  # 0.05 -> 0.50
                    queue_length += int(progress * 10)
                    wip += int(progress * 6)
                    is_anomaly = True

                    if step >= 45:
                        machine_state = "FAULT"
                        utilization = 0.35
                    elif step >= 30:
                        machine_state = "WARNING"

            # SCENARIO 3: Sudden Machine Failure on S2
            elif scenario == ScenarioType.SUDDEN_FAILURE and st_id == "S2":
                if step >= 25:
                    # Instant tool breakage / jam
                    cycle_time = 0.0
                    motor_current = 19.5 + np_rng.normal(0, 0.5)
                    vibration = 0.65 + np_rng.normal(0, 0.05)
                    temperature += 30.0
                    current_variance = 1.2
                    utilization = 0.0
                    queue_length += 12
                    machine_state = "DOWN"
                    is_anomaly = True

            # SCENARIO 5: Other Station Disturbance on S5 (Weld Jitter)
            elif scenario == ScenarioType.OTHER_STATION_DISTURBANCE and st_id == "S5":
                if 20 <= step <= 45:
                    vibration += 0.25
                    current_variance += 0.20
                    cycle_time += 8.0
                    is_anomaly = True

            # Associated upstream buffer updates
            if st_id == "S1":
                buf_key = "B1"
            elif st_id == "S2":
                buf_key = "B2"
            elif st_id == "S3":
                buf_key = "B3"
            elif st_id == "S4":
                buf_key = "B4"
            else:
                buf_key = "B5"

            connected_occ = buffer_occupancies[buf_key]

            # Adjust buffer dynamics under bottleneck
            if scenario == ScenarioType.GRADUAL_S3_DEGRADATION:
                if step >= 25:
                    # Upstream buffer B2 fills up towards saturation
                    buffer_occupancies["B2"] = min(10.0, 3.0 + (step - 25) * 0.35)
                    # Downstream buffer B3 starves
                    buffer_occupancies["B3"] = max(0.2, 3.0 - (step - 25) * 0.15)
            elif scenario == ScenarioType.SUDDEN_FAILURE:
                if step >= 25:
                    buffer_occupancies["B1"] = min(10.0, 3.0 + (step - 25) * 0.5)
                    buffer_occupancies["B2"] = max(0.1, 3.0 - (step - 25) * 0.2)

            # SCENARIO 4: Sensor Missingness / Dropouts (Random Nulls)
            st_dict = {
                "station_id": st_id,
                "cycle_time": round(cycle_time, 2),
                "cycle_time_delta": round(cycle_time - base_p["cycle_time"], 2),
                "utilization": round(utilization, 4),
                "queue_length": queue_length,
                "queue": queue_length,
                "wip": wip,
                "WIP": wip,
                "temperature": round(temperature, 2),
                "vibration": round(vibration, 4),
                "motor_current": round(motor_current, 2),
                "current_variance": round(current_variance, 4),
                "buffer_occupancy": round(connected_occ, 2),
                "machine_state": machine_state,
                "state": machine_state,
                "timestamp": t,
            }

            if scenario == ScenarioType.SENSOR_MISSINGNESS:
                # Randomly drop 20% of sensor channels
                for sensor_key in ["temperature", "vibration", "motor_current", "current_variance"]:
                    if rng.random() < 0.20:
                        st_dict[sensor_key] = None

            stations_data[st_id] = st_dict
            gt_anomalies[st_id] = is_anomaly
            gt_failures[st_id] = gt_failure_time if is_anomaly else None

        buffers_data = {
            f"B{k}": {
                "buffer_id": f"B{k}",
                "occupancy": round(buffer_occupancies[f"B{k}"], 2),
                "capacity": buffer_capacities[f"B{k}"],
                "upstream": f"S{k}",
                "downstream": f"S{k+1}",
            }
            for k in range(1, 6)
        }

        snapshots.append(
            TelemetrySnapshot(
                run_id=run_id,
                step_index=step,
                timestamp=t,
                scenario=scenario.value,
                stations=stations_data,
                buffers=buffers_data,
                ground_truth_anomalies=gt_anomalies,
                ground_truth_failure_times=gt_failures,
            )
        )

    return snapshots


def generate_full_factory_dataset(
    n_train_runs: int = 6,
    n_val_runs: int = 2,
    steps_per_run: int = 50,
    random_seed: int = 42,
) -> Dict[str, List[TelemetrySnapshot]]:
    """
    Generates the complete multi-run partitioned dataset:
    - Train: 6 nominal runs (runs 1-6)
    - Val: 2 nominal runs (runs 7-8)
    - Test: 5 multi-scenario runs (runs 9-14)

    Returns:
        Dictionary mapping split name ("train", "val", "test") to lists of TelemetrySnapshot.
    """
    dataset: Dict[str, List[TelemetrySnapshot]] = {
        "train": [],
        "val": [],
        "test": [],
    }

    # 1. Training Runs (Strictly nominal operations)
    for i in range(1, n_train_runs + 1):
        run_id = f"run_{i:03d}"
        seed = random_seed + i
        snaps = simulate_factory_run(
            run_id=run_id,
            scenario=ScenarioType.NORMAL,
            total_steps=steps_per_run,
            random_seed=seed,
        )
        dataset["train"].extend(snaps)

    # 2. Validation Runs (Nominal operations for threshold calibration)
    for j in range(1, n_val_runs + 1):
        run_id = f"run_{n_train_runs + j:03d}"
        seed = random_seed + 100 + j
        snaps = simulate_factory_run(
            run_id=run_id,
            scenario=ScenarioType.NORMAL,
            total_steps=steps_per_run,
            random_seed=seed,
        )
        dataset["val"].extend(snaps)

    # 3. Test Runs (5 distinct scenarios)
    test_scenarios = [
        ("run_009", ScenarioType.NORMAL),
        ("run_010", ScenarioType.GRADUAL_S3_DEGRADATION),
        ("run_011", ScenarioType.GRADUAL_S3_DEGRADATION),
        ("run_012", ScenarioType.SUDDEN_FAILURE),
        ("run_013", ScenarioType.SENSOR_MISSINGNESS),
        ("run_014", ScenarioType.OTHER_STATION_DISTURBANCE),
    ]

    for idx, (run_id, scn) in enumerate(test_scenarios):
        seed = random_seed + 200 + idx
        snaps = simulate_factory_run(
            run_id=run_id,
            scenario=scn,
            total_steps=steps_per_run,
            random_seed=seed,
        )
        dataset["test"].extend(snaps)

    return dataset
