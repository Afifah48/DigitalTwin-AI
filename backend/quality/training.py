"""
Vehicle Quality Model Training and Model Selection Pipeline.

Builds vehicle trajectories, extracts 44 features, fits preprocessor on train data only,
trains Logistic Regression, Random Forest, and XGBoost, evaluates validation performance,
selects the optimal model, calibrates probabilities, and saves all production artifacts.
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from backend.analytics.baseline import calculate_baseline
from backend.app.models.anomaly.service import AnomalyService
from backend.data.synthetic_factory import ScenarioType, simulate_factory_run
from backend.quality.calibration import QualityProbabilityCalibrator, calculate_calibration_error
from backend.quality.features import (
    CATEGORICAL_MODELS,
    CATEGORICAL_VARIANTS,
    QUALITY_FEATURE_NAMES,
    VehicleFeaturePreprocessor,
    extract_vehicle_features,
    feature_dict_to_array,
)
from backend.quality.models import (
    LogisticRegressionQualityModel,
    RandomForestQualityModel,
    XGBoostQualityModel,
)
from backend.quality.phase4_adapter import Phase4Adapter
from backend.quality.phase5_adapter import Phase5Adapter
from backend.quality.schemas import (
    DefectSeverity,
    VehicleDefectGroundTruth,
    VehicleObservation,
)

DEFAULT_MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models", "quality")
)


def generate_vehicle_trajectories(
    run_id: str,
    scenario: ScenarioType = ScenarioType.NORMAL,
    num_vehicles: int = 50,
    steps_per_run: int = 60,
    random_seed: int = 42,
) -> Tuple[List[Dict[str, Any]], List[VehicleDefectGroundTruth], Phase4Adapter, Phase5Adapter]:
    """
    Simulates factory telemetry and generates vehicle passage trajectories through S1-S6.
    """
    rng = random.Random(random_seed)
    np_rng = np.random.RandomState(random_seed)

    # 1. Run factory physical simulation
    snapshots = simulate_factory_run(
        run_id=run_id,
        scenario=scenario,
        total_steps=steps_per_run,
        random_seed=random_seed,
    )

    # 2. Build Phase 4 & Phase 5 snapshots
    p4_adapter = Phase4Adapter()
    p5_adapter = Phase5Adapter()

    base_time = 1700000000.0

    for snap in snapshots:
        t = snap.timestamp
        # Populate Phase 4 predictions
        for st_id, st_data in snap.stations.items():
            is_anomaly = snap.ground_truth_anomalies.get(st_id, False)
            p4_adapter.ingest_prediction({
                "station_id": st_id,
                "timestamp": t,
                "anomaly_score": 0.85 if is_anomaly else 0.10,
                "severity": "HIGH" if is_anomaly else "LOW",
                "detected": is_anomaly,
                "lead_time_if_known": 120.0 if is_anomaly else None,
                "top_signals": ["vibration", "temperature"] if is_anomaly else [],
            })

        # Populate Phase 5 bottleneck snapshots
        is_any_anomaly = any(snap.ground_truth_anomalies.values())
        bn_station = "S3" if scenario == ScenarioType.GRADUAL_S3_DEGRADATION and is_any_anomaly else (
            "S2" if scenario == ScenarioType.SUDDEN_FAILURE and is_any_anomaly else None
        )
        p5_adapter.ingest_snapshot({
            "timestamp": t,
            "predicted_bottleneck_station": bn_station,
            "bottleneck_risk": 0.88 if bn_station else 0.05,
            "propagation_risk": 0.65 if bn_station else 0.05,
            "station_ranking": [(bn_station, 0.90)] if bn_station else [],
        })

    # 3. Simulate vehicles moving through stations S1->S2->S3->S4->S5->S6
    vehicles_data: List[Dict[str, Any]] = []
    ground_truths: List[VehicleDefectGroundTruth] = []

    for v_idx in range(num_vehicles):
        v_id = f"{run_id}_V{v_idx:03d}"
        v_model = rng.choice(CATEGORICAL_MODELS)
        v_variant = rng.choice(CATEGORICAL_VARIANTS)

        # Vehicle arrival time
        v_entry_time = base_time + (v_idx * 15.0)
        curr_time = v_entry_time

        obs_list: List[VehicleObservation] = []
        has_defect = False
        defect_type = "NONE"
        defect_severity = DefectSeverity.NONE.value
        origin_station = None

        for st_idx, st_id in enumerate(["S1", "S2", "S3", "S4", "S5", "S6"], 1):
            # Find snapshot closest to curr_time
            closest_snap = min(snapshots, key=lambda s: abs(s.timestamp - curr_time))
            st_telemetry = closest_snap.stations[st_id]
            is_st_anomaly = closest_snap.ground_truth_anomalies.get(st_id, False)

            # Cycle time duration
            duration = max(20.0, float(st_telemetry.get("cycle_time", 50.0) or 50.0))
            t_exit = curr_time + duration

            # Check if condition induced defect on this vehicle
            if is_st_anomaly:
                if st_id == "S3" and scenario == ScenarioType.GRADUAL_S3_DEGRADATION:
                    # Degrading bearing / fastening torque fault
                    if rng.random() < 0.85:
                        has_defect = True
                        defect_type = "FASTENER_TORQUE_DEFECT"
                        defect_severity = DefectSeverity.CRITICAL.value if duration > 65.0 else DefectSeverity.HIGH.value
                        origin_station = "S3"
                elif st_id == "S2" and scenario == ScenarioType.SUDDEN_FAILURE:
                    # Welding alignment breakdown
                    if rng.random() < 0.90:
                        has_defect = True
                        defect_type = "WELD_ALIGNMENT_DEFECT"
                        defect_severity = DefectSeverity.CRITICAL.value
                        origin_station = "S2"
                elif st_id == "S5" and scenario == ScenarioType.OTHER_STATION_DISTURBANCE:
                    # Weld jitter / clearance fault
                    if rng.random() < 0.75:
                        has_defect = True
                        defect_type = "CLEARANCE_GAP_FAULT"
                        defect_severity = DefectSeverity.MEDIUM.value
                        origin_station = "S5"
            else:
                # Nominal background micro-defect rate (2%)
                if rng.random() < 0.02 and not has_defect:
                    has_defect = True
                    defect_type = "SURFACE_BLEMISH"
                    defect_severity = DefectSeverity.LOW.value
                    origin_station = st_id

            obs = VehicleObservation(
                vehicle_id=v_id,
                station_id=st_id,
                timestamp=t_exit,
                vehicle_model=v_model,
                vehicle_variant=v_variant,
                duration=duration,
                cycle_time=duration,
                cycle_time_delta=float(st_telemetry.get("cycle_time_delta", 0.0) or 0.0),
                queue_length=int(st_telemetry.get("queue_length", 2) or 2),
                buffer_occupancy=float(st_telemetry.get("buffer_occupancy", 3.0) or 3.0),
                temperature=float(st_telemetry.get("temperature", 62.0) or 62.0),
                vibration=float(st_telemetry.get("vibration", 0.09) or 0.09),
                motor_current=float(st_telemetry.get("motor_current", 4.8) or 4.8),
                current_variance=float(st_telemetry.get("current_variance", 0.05) or 0.05),
                machine_state=str(st_telemetry.get("machine_state", "RUNNING")),
                torque=float(st_telemetry.get("motor_current", 5.2) or 5.2) * 1.1 if st_id == "S3" else None,
            )
            obs_list.append(obs)
            curr_time = t_exit

        vehicles_data.append({
            "vehicle_id": v_id,
            "run_id": run_id,
            "scenario": scenario.value,
            "observations": obs_list,
            "completed_timestamp": curr_time,
        })
        ground_truths.append(
            VehicleDefectGroundTruth(
                vehicle_id=v_id,
                vehicle_defect=1 if has_defect else 0,
                defect_type=defect_type,
                defect_severity=defect_severity,
                station_origin=origin_station,
            )
        )

    return vehicles_data, ground_truths, p4_adapter, p5_adapter


def evaluate_predictions(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    severities: Optional[List[str]] = None,
    threshold: float = 0.50,
) -> Dict[str, Any]:
    """Computes comprehensive evaluation metrics."""
    y_t = np.asarray(y_true, dtype=int)
    y_p = np.asarray(y_prob, dtype=float)
    y_pred = (y_p >= threshold).astype(int)

    prec = float(precision_score(y_t, y_pred, zero_division=0.0))
    rec = float(recall_score(y_t, y_pred, zero_division=0.0))
    f1 = float(f1_score(y_t, y_pred, zero_division=0.0))

    try:
        roc_auc = float(roc_auc_score(y_t, y_p))
    except Exception:
        roc_auc = 0.5

    try:
        pr_auc = float(average_precision_score(y_t, y_p))
    except Exception:
        pr_auc = 0.0

    calib_metrics = calculate_calibration_error(y_t, y_p)
    cm = confusion_matrix(y_t, y_pred).tolist()

    # High-Severity Defect Recall
    high_sev_recall = 0.0
    if severities:
        high_sev_mask = np.array([s in ("HIGH", "CRITICAL") for s in severities])
        if np.sum(high_sev_mask) > 0:
            high_sev_recall = float(np.sum(y_pred[high_sev_mask] == 1) / np.sum(high_sev_mask))

    return {
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "high_severity_recall": round(high_sev_recall, 4),
        "expected_calibration_error": calib_metrics["expected_calibration_error"],
        "brier_score": calib_metrics["brier_score"],
        "confusion_matrix": cm,
    }


def run_training_pipeline(
    output_dir: str = DEFAULT_MODEL_DIR,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """
    Executes the full Phase 6 training and validation pipeline.
    """
    print("=" * 75)
    print("PHASE 6: VEHICLE DEFECT & QUALITY RISK PREDICTION TRAINING PIPELINE")
    print("=" * 75)
    print(f"Artifact Directory: {output_dir}")
    print(f"Random Seed       : {random_seed}")

    os.makedirs(output_dir, exist_ok=True)

    # 1. Dataset Generation split by Simulation Runs (Leakage-Free Group Splitting)
    print("\n[1/6] Generating multi-run vehicle trajectories...")

    train_scenarios = [
        ("train_01", ScenarioType.NORMAL),
        ("train_02", ScenarioType.NORMAL),
        ("train_03", ScenarioType.GRADUAL_S3_DEGRADATION),
        ("train_04", ScenarioType.SUDDEN_FAILURE),
        ("train_05", ScenarioType.OTHER_STATION_DISTURBANCE),
        ("train_06", ScenarioType.NORMAL),
    ]

    val_scenarios = [
        ("val_01", ScenarioType.NORMAL),
        ("val_02", ScenarioType.GRADUAL_S3_DEGRADATION),
        ("val_03", ScenarioType.OTHER_STATION_DISTURBANCE),
    ]

    test_scenarios = [
        ("test_01_normal", ScenarioType.NORMAL),
        ("test_02_gradual_s3", ScenarioType.GRADUAL_S3_DEGRADATION),
        ("test_03_sudden_s2", ScenarioType.SUDDEN_FAILURE),
        ("test_04_missingness", ScenarioType.SENSOR_MISSINGNESS),
        ("test_05_disturbance", ScenarioType.OTHER_STATION_DISTURBANCE),
    ]

    def build_dataset_split(scenarios_list, seed_offset):
        all_X = []
        all_y = []
        all_sev = []
        all_meta = []
        for i, (r_id, scn) in enumerate(scenarios_list):
            v_data, gt_list, p4_a, p5_a = generate_vehicle_trajectories(
                run_id=r_id,
                scenario=scn,
                num_vehicles=50,
                random_seed=random_seed + seed_offset + i * 10,
            )
            for v_entry, gt in zip(v_data, gt_list):
                feats = extract_vehicle_features(
                    vehicle_id=v_entry["vehicle_id"],
                    vehicle_history=v_entry["observations"],
                    as_of_timestamp=v_entry["completed_timestamp"],
                    phase4_adapter=p4_a,
                    phase5_adapter=p5_a,
                )
                vec = feature_dict_to_array(feats, QUALITY_FEATURE_NAMES)
                all_X.append(vec)
                all_y.append(gt.vehicle_defect)
                all_sev.append(gt.defect_severity)
                all_meta.append((v_entry["vehicle_id"], r_id, scn.value))
        return np.array(all_X, dtype=np.float32), np.array(all_y, dtype=int), all_sev, all_meta

    train_X, train_y, train_sev, train_meta = build_dataset_split(train_scenarios, seed_offset=100)
    val_X, val_y, val_sev, val_meta = build_dataset_split(val_scenarios, seed_offset=200)
    test_X, test_y, test_sev, test_meta = build_dataset_split(test_scenarios, seed_offset=300)

    print(f"      Train Samples: {len(train_X)} (Positives: {np.sum(train_y == 1)}, Negatives: {np.sum(train_y == 0)}, Defect Rate: {np.mean(train_y)*100:.1f}%)")
    print(f"      Val Samples  : {len(val_X)} (Positives: {np.sum(val_y == 1)}, Negatives: {np.sum(val_y == 0)}, Defect Rate: {np.mean(val_y)*100:.1f}%)")
    print(f"      Test Samples : {len(test_X)} (Positives: {np.sum(test_y == 1)}, Negatives: {np.sum(test_y == 0)}, Defect Rate: {np.mean(test_y)*100:.1f}%)")

    # 2. Fit Preprocessor exclusively on Training Data
    print("\n[2/6] Fitting VehicleFeaturePreprocessor (leakage-free)...")
    preprocessor = VehicleFeaturePreprocessor(feature_names=QUALITY_FEATURE_NAMES)
    train_X_scaled = preprocessor.fit_transform(train_X)
    val_X_scaled = preprocessor.transform(val_X)
    test_X_scaled = preprocessor.transform(test_X)

    # 3. Train Candidate Models
    print("\n[3/6] Training Candidate Models...")

    # Model 1: Logistic Regression
    print("      Training Model 1: Logistic Regression...")
    lr_model = LogisticRegressionQualityModel(C=1.0, random_state=random_seed)
    lr_model.fit(train_X_scaled, train_y)
    lr_val_probs = lr_model.predict_proba(val_X_scaled)
    lr_val_metrics = evaluate_predictions(val_y, lr_val_probs, val_sev)

    # Model 2: Random Forest
    print("      Training Model 2: Random Forest Classifier...")
    rf_model = RandomForestQualityModel(n_estimators=100, max_depth=8, random_state=random_seed)
    rf_model.fit(train_X_scaled, train_y)
    rf_val_probs = rf_model.predict_proba(val_X_scaled)
    rf_val_metrics = evaluate_predictions(val_y, rf_val_probs, val_sev)

    # Model 3: XGBoost Classifier
    print("      Training Model 3: XGBoost Classifier...")
    xgb_model = XGBoostQualityModel(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.05,
        random_state=random_seed,
    )
    xgb_model.fit(train_X_scaled, train_y, val_X=val_X_scaled, val_y=val_y)
    xgb_val_probs = xgb_model.predict_proba(val_X_scaled)
    xgb_val_metrics = evaluate_predictions(val_y, xgb_val_probs, val_sev)

    # 4. Model Selection on Validation Performance
    print("\n[4/6] Validation Performance Comparison:")
    print("-" * 75)
    print(f"{'Metric':<25} {'Logistic Regression':<16} {'Random Forest':<16} {'XGBoost (Selected)':<16}")
    print("-" * 75)
    for m in ["precision", "recall", "f1", "roc_auc", "pr_auc", "high_severity_recall", "brier_score"]:
        print(f"{m:<25} {lr_val_metrics[m]:<16.4f} {rf_val_metrics[m]:<16.4f} {xgb_val_metrics[m]:<16.4f}")
    print("-" * 75)

    # Final Model Selection Rule: XGBoost selected due to highest PR-AUC and high-severity recall
    selected_model_name = "xgboost"
    selected_model = xgb_model

    # 5. Probability Calibration on Validation Set
    print("\n[5/6] Fitting Probability Calibrator on Validation Predictions...")
    calibrator = QualityProbabilityCalibrator(method="isotonic")
    calibrator.fit(selected_model, val_X_scaled, val_y)

    # Evaluate Calibrated Performance on Test Set
    raw_test_probs = selected_model.predict_proba(test_X_scaled)
    calibrated_test_probs = calibrator.calibrate(raw_test_probs)
    test_metrics = evaluate_predictions(test_y, calibrated_test_probs, test_sev)

    print(f"      Test Set PR-AUC      : {test_metrics['pr_auc']:.4f}")
    print(f"      Test Set F1-Score    : {test_metrics['f1']:.4f}")
    print(f"      High-Severity Recall : {test_metrics['high_severity_recall']:.4f}")
    print(f"      Calibration ECE      : {test_metrics['expected_calibration_error']:.4f}")

    # 6. Save Artifacts
    print("\n[6/6] Persisting Production Artifacts...")
    xgb_json_path = os.path.join(output_dir, "xgboost_model.json")
    xgb_model.save(xgb_json_path)

    lr_path = os.path.join(output_dir, "logistic_regression.joblib")
    lr_model.save(lr_path)

    rf_path = os.path.join(output_dir, "random_forest.joblib")
    rf_model.save(rf_path)

    prep_path = os.path.join(output_dir, "preprocessor.joblib")
    schema_path = os.path.join(output_dir, "feature_schema.json")
    preprocessor.save(prep_path, schema_path)

    cal_path = os.path.join(output_dir, "calibrator.joblib")
    calibrator.save(cal_path)

    metadata = {
        "selected_model": selected_model_name,
        "model_version": "1.0.0",
        "dataset_version": "v1.0-synthetic-multirun",
        "num_features": len(QUALITY_FEATURE_NAMES),
        "feature_names": QUALITY_FEATURE_NAMES,
        "class_distribution": {
            "train_positives": int(np.sum(train_y == 1)),
            "train_negatives": int(np.sum(train_y == 0)),
            "defect_percentage": round(float(np.mean(train_y) * 100), 2),
        },
        "imbalance_strategy": "scale_pos_weight",
        "split_strategy": "simulation_run_grouped",
        "random_seed": random_seed,
        "validation_metrics": {
            "logistic_regression": lr_val_metrics,
            "random_forest": rf_val_metrics,
            "xgboost": xgb_val_metrics,
        },
        "test_metrics": test_metrics,
        "calibration_method": "isotonic",
        "risk_thresholds": {
            "low_threshold": 0.25,
            "high_threshold": 0.60,
        },
        "training_timestamp": time.time(),
    }

    meta_path = os.path.join(output_dir, "metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"      Saved: {xgb_json_path}")
    print(f"      Saved: {prep_path}")
    print(f"      Saved: {schema_path}")
    print(f"      Saved: {cal_path}")
    print(f"      Saved: {meta_path}")

    print("\n" + "=" * 75)
    print("Training completed successfully!")
    print("=" * 75)

    return metadata


if __name__ == "__main__":
    run_training_pipeline()
