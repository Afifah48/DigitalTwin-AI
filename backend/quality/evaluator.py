"""
Offline Benchmark Evaluator for Phase 6 Vehicle Quality Prediction.

Computes comprehensive offline metrics (Precision, Recall, F1, ROC-AUC, PR-AUC,
High-Severity Recall, Expected Calibration Error, Confusion Matrix, and Scenario Breakdowns).

CLI Usage:
    python -m backend.quality.evaluator
    python -m backend.quality.evaluator --data-dir backend/models/quality
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional
import numpy as np

from backend.data.synthetic_factory import ScenarioType
from backend.quality.calibration import calculate_calibration_error
from backend.quality.features import QUALITY_FEATURE_NAMES, extract_vehicle_features, feature_dict_to_array
from backend.quality.service import QualityRiskService
from backend.quality.training import evaluate_predictions, generate_vehicle_trajectories

DEFAULT_MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models", "quality")
)


def run_offline_evaluation(
    models_dir: str = DEFAULT_MODEL_DIR,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """
    Evaluates the trained QualityRiskService against a held-out test suite across 5 scenarios.
    """
    print("=" * 80)
    print("PHASE 6: OFFLINE VEHICLE DEFECT PREDICTION EVALUATION BENCHMARK")
    print("=" * 80)
    print(f"Loading model artifacts from: {models_dir}")

    service = QualityRiskService()
    service.load_artifacts(models_dir, model_type="xgboost")

    test_scenarios = [
        ("test_01_normal", ScenarioType.NORMAL),
        ("test_02_gradual_s3", ScenarioType.GRADUAL_S3_DEGRADATION),
        ("test_03_sudden_s2", ScenarioType.SUDDEN_FAILURE),
        ("test_04_missingness", ScenarioType.SENSOR_MISSINGNESS),
        ("test_05_disturbance", ScenarioType.OTHER_STATION_DISTURBANCE),
    ]

    all_y_true: List[int] = []
    all_y_prob: List[float] = []
    all_y_pred: List[int] = []
    all_severities: List[str] = []

    scenario_results: Dict[str, Dict[str, Any]] = {}

    total_vehicles = 0

    for r_idx, (r_id, scn) in enumerate(test_scenarios):
        v_data, gt_list, p4_a, p5_a = generate_vehicle_trajectories(
            run_id=r_id,
            scenario=scn,
            num_vehicles=50,
            random_seed=random_seed + 300 + r_idx * 10,
        )

        scn_y_true = []
        scn_y_prob = []
        scn_severities = []

        for v_entry, gt in zip(v_data, gt_list):
            pred = service.predict(
                vehicle_id=v_entry["vehicle_id"],
                vehicle_history=v_entry["observations"],
                as_of_timestamp=v_entry["completed_timestamp"],
                phase4_adapter=p4_a,
                phase5_adapter=p5_a,
            )

            prob = pred.defect_probability
            y_t = gt.vehicle_defect

            all_y_true.append(y_t)
            all_y_prob.append(prob)
            all_y_pred.append(1 if prob >= 0.50 else 0)
            all_severities.append(gt.defect_severity)

            scn_y_true.append(y_t)
            scn_y_prob.append(prob)
            scn_severities.append(gt.defect_severity)
            total_vehicles += 1

        scn_metrics = evaluate_predictions(
            np.array(scn_y_true),
            np.array(scn_y_prob),
            scn_severities,
        )
        scenario_results[scn.value] = scn_metrics

    # Overall Metrics
    overall_metrics = evaluate_predictions(
        np.array(all_y_true),
        np.array(all_y_prob),
        all_severities,
    )

    print("\n" + "=" * 80)
    print("OVERALL HELD-OUT TEST BENCHMARK RESULTS")
    print("=" * 80)
    print(f"{'Metric':<35} {'Score':<15}")
    print("-" * 50)
    print(f"{'ROC-AUC':<35} {overall_metrics['roc_auc']:.4f}")
    print(f"{'PR-AUC':<35} {overall_metrics['pr_auc']:.4f}")
    print(f"{'Precision':<35} {overall_metrics['precision']:.4f}")
    print(f"{'Recall':<35} {overall_metrics['recall']:.4f}")
    print(f"{'F1-Score':<35} {overall_metrics['f1']:.4f}")
    print(f"{'High-Severity Defect Recall':<35} {overall_metrics['high_severity_recall']:.4f}")
    print(f"{'Expected Calibration Error (ECE)':<35} {overall_metrics['expected_calibration_error']:.4f}")
    print(f"{'Brier Score Loss':<35} {overall_metrics['brier_score']:.4f}")
    print("-" * 50)
    print(f"Confusion Matrix [TN, FP], [FN, TP]: {overall_metrics['confusion_matrix']}")

    print("\n" + "=" * 80)
    print("PER-SCENARIO PERFORMANCE BREAKDOWN")
    print("=" * 80)
    print(f"{'Scenario':<30} {'Precision':<12} {'Recall':<12} {'F1':<12} {'PR-AUC':<12}")
    print("-" * 80)
    for scn_name, m in scenario_results.items():
        print(f"{scn_name:<30} {m['precision']:<12.4f} {m['recall']:<12.4f} {m['f1']:<12.4f} {m['pr_auc']:<12.4f}")
    print("=" * 80)

    report_payload = {
        "models_dir": models_dir,
        "total_test_vehicles": total_vehicles,
        "overall": overall_metrics,
        "scenarios": scenario_results,
    }

    eval_json_path = os.path.join(models_dir, "evaluation_results.json")
    with open(eval_json_path, "w") as f:
        json.dump(report_payload, f, indent=2)
    print(f"\nSaved evaluation results to: {eval_json_path}")

    return report_payload


def main():
    parser = argparse.ArgumentParser(description="Phase 6 Vehicle Defect Prediction Offline Evaluator")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=DEFAULT_MODEL_DIR,
        help="Path to models and artifacts directory",
    )
    args = parser.parse_args()
    run_offline_evaluation(models_dir=args.data_dir)


if __name__ == "__main__":
    main()
