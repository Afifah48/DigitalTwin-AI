"""
Example Anomaly Prediction Demonstration.

Loads the trained models from disk and demonstrates real-time inference on
normal vs degraded station telemetry, printing full AnomalyPrediction outputs.
"""

import json
import os
from pprint import pprint

from backend.analytics.baseline import calculate_baseline
from backend.app.models.anomaly.service import AnomalyService
from backend.data.synthetic_factory import generate_full_factory_dataset

DEFAULT_MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models", "anomaly")
)


def run_demo():
    print("=" * 70)
    print("PHASE 4: LIVE ANOMALY DETECTION INFERENCE DEMO")
    print("=" * 70)

    # 1. Initialize service and load artifacts
    service = AnomalyService()
    service.load_artifacts(DEFAULT_MODEL_DIR, preferred_model="if")

    dataset = generate_full_factory_dataset(n_train_runs=2, n_val_runs=1, steps_per_run=10)
    baseline = calculate_baseline([s.to_dict() for s in dataset["train"]])
    service.set_baseline(baseline)

    # 2. Case A: Station S3 in Normal Operation
    print("\n--- [CASE A] Normal S3 Telemetry ---")
    normal_s3_telemetry = {
        "cycle_time": 54.2,
        "utilization": 0.88,
        "queue_length": 2,
        "wip": 2,
        "temperature": 65.1,
        "vibration": 0.10,
        "motor_current": 5.2,
        "current_variance": 0.05,
        "machine_state": "RUNNING",
    }
    pred_normal = service.predict_station(
        station_id="S3",
        station_telemetry=normal_s3_telemetry,
        timestamp=1700000000.0,
        connected_buffer_occupancy=3.2,
    )
    print(f"Station ID       : {pred_normal.station_id}")
    print(f"Anomaly Score    : {pred_normal.anomaly_score:.4f}")
    print(f"Severity Level   : {pred_normal.severity}")
    print(f"Anomaly Detected : {pred_normal.detected}")
    print(f"Top Signals      : {pred_normal.top_signals}")

    # 3. Case B: Station S3 in Degrading Bearing Condition
    print("\n--- [CASE B] Degrading S3 Telemetry (Elevated vibration & current variance) ---")
    degraded_s3_telemetry = {
        "cycle_time": 66.5,          # +12.5s over nominal 54s
        "utilization": 0.65,
        "queue_length": 8,
        "wip": 6,
        "temperature": 82.3,         # +17°C
        "vibration": 0.38,           # +3.8x normal
        "motor_current": 8.7,        # +3.5A
        "current_variance": 0.42,    # +8.4x normal
        "machine_state": "WARNING",
    }
    pred_degraded = service.predict_station(
        station_id="S3",
        station_telemetry=degraded_s3_telemetry,
        timestamp=1700000060.0,
        connected_buffer_occupancy=8.5,
        ground_truth_failure_time=1700000240.0,  # Failure scheduled at t=240s
    )
    print(f"Station ID       : {pred_degraded.station_id}")
    print(f"Anomaly Score    : {pred_degraded.anomaly_score:.4f}")
    print(f"Severity Level   : {pred_degraded.severity}")
    print(f"Anomaly Detected : {pred_degraded.detected}")
    print(f"Detection Lead   : {pred_degraded.lead_time_if_known} seconds warning before failure")
    print(f"Top Signals      : {pred_degraded.top_signals}")

    # 4. Case C: Full Factory Snapshot Batch Prediction
    print("\n--- [CASE C] Full Factory Snapshot Batch Prediction ---")
    factory_snapshot = {
        "timestamp": 1700000100.0,
        "stations": {
            "S1": {"cycle_time": 45.1, "cycle_time_delta": 0.1, "utilization": 0.82, "queue_length": 2, "wip": 2, "temperature": 60.0, "vibration": 0.08, "motor_current": 4.5, "current_variance": 0.04, "state": "RUNNING"},
            "S2": {"cycle_time": 48.0, "cycle_time_delta": 0.0, "utilization": 0.84, "queue_length": 2, "wip": 2, "temperature": 62.1, "vibration": 0.09, "motor_current": 4.8, "current_variance": 0.05, "state": "RUNNING"},
            "S3": degraded_s3_telemetry,
            "S4": {"cycle_time": 50.2, "cycle_time_delta": 0.2, "utilization": 0.85, "queue_length": 2, "wip": 2, "temperature": 63.0, "vibration": 0.09, "motor_current": 5.0, "current_variance": 0.05, "state": "RUNNING"},
            "S5": {"cycle_time": 46.0, "cycle_time_delta": 0.0, "utilization": 0.83, "queue_length": 2, "wip": 2, "temperature": 61.2, "vibration": 0.08, "motor_current": 4.6, "current_variance": 0.04, "state": "RUNNING"},
            "S6": {"cycle_time": 44.1, "cycle_time_delta": 0.1, "utilization": 0.80, "queue_length": 2, "wip": 2, "temperature": 59.0, "vibration": 0.07, "motor_current": 4.4, "current_variance": 0.04, "state": "RUNNING"},
        },
        "buffers": {
            "B1": {"occupancy": 3.0, "capacity": 10.0},
            "B2": {"occupancy": 8.5, "capacity": 10.0},
            "B3": {"occupancy": 1.2, "capacity": 10.0},
            "B4": {"occupancy": 2.5, "capacity": 10.0},
            "B5": {"occupancy": 3.0, "capacity": 10.0},
        },
    }
    batch_res = service.predict_factory_snapshot(factory_snapshot)
    print(f"Anomalous Stations : {batch_res.anomalous_stations}")
    print(f"Highest Anomaly    : Station {batch_res.highest_anomaly_station} (Score: {batch_res.max_anomaly_score:.4f})")

    print("\n" + "=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
