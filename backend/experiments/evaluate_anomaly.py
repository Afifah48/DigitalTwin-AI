"""
Evaluation and Benchmarking Script for Phase 4 ML Anomaly Subsystems.

Evaluates Model A (Isolation Forest) and Model B (LSTM Autoencoder) across 5 realistic
simulation scenarios and calculates Precision, Recall, F1, ROC-AUC, PR-AUC,
False Positive Rate, and Mean Detection Lead Time.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.metrics import (
    auc,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

from backend.analytics.baseline import calculate_baseline
from backend.app.models.anomaly.features import FeatureScaler
from backend.app.models.anomaly.isolation_forest import IsolationForestAnomalyModel
from backend.app.models.anomaly.lstm_autoencoder import LSTMAutoencoderModel
from backend.app.models.anomaly.service import AnomalyService
from backend.data.synthetic_factory import (
    ScenarioType,
    TelemetrySnapshot,
    generate_full_factory_dataset,
)

DEFAULT_MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models", "anomaly")
)


def calculate_metrics(
    y_true: List[int],
    y_pred: List[int],
    y_scores: List[float],
) -> Dict[str, float]:
    """
    Computes Precision, Recall, F1, ROC-AUC, PR-AUC, and FPR safely.
    """
    y_t = np.array(y_true, dtype=int)
    y_p = np.array(y_pred, dtype=int)
    y_s = np.array(y_scores, dtype=float)

    n_pos = int(np.sum(y_t == 1))
    n_neg = int(np.sum(y_t == 0))

    prec = float(precision_score(y_t, y_p, zero_division=0.0))
    rec = float(recall_score(y_t, y_p, zero_division=0.0))
    f1 = float(f1_score(y_t, y_p, zero_division=0.0))

    # Confusion matrix for FPR: FP / (FP + TN)
    if n_neg > 0:
        tn, fp, fn, tp = confusion_matrix(y_t, y_p, labels=[0, 1]).ravel()
        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    else:
        fpr = 0.0

    # ROC-AUC (requires both positive and negative classes)
    if n_pos > 0 and n_neg > 0:
        try:
            roc_auc = float(roc_auc_score(y_t, y_s))
        except Exception:
            roc_auc = 0.5
        try:
            p_curve, r_curve, _ = precision_recall_curve(y_t, y_s)
            pr_auc = float(auc(r_curve, p_curve))
        except Exception:
            pr_auc = 0.0
    else:
        # Fallbacks when only negative (nominal) or only positive exists
        roc_auc = 1.0 if (n_neg > 0 and np.sum(y_p) == 0) else 0.5
        pr_auc = 1.0 if (n_neg > 0 and np.sum(y_p) == 0) else 0.0

    return {
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "false_positive_rate": round(fpr, 4),
    }


def evaluate_model_on_test_runs(
    model: Any,
    test_snapshots: List[TelemetrySnapshot],
    scaler: FeatureScaler,
    baseline: Any,
    model_name: str,
) -> Dict[str, Any]:
    """
    Evaluates an anomaly detector on test snapshots, tracking lead time for degradation scenarios.
    """
    service = AnomalyService(model=model, scaler=scaler, baseline=baseline)

    # Group snapshots by run
    runs_map: Dict[str, List[TelemetrySnapshot]] = {}
    for s in test_snapshots:
        runs_map.setdefault(s.run_id, []).append(s)

    all_y_true: List[int] = []
    all_y_pred: List[int] = []
    all_y_scores: List[float] = []

    scenario_metrics: Dict[str, Dict[str, float]] = {}
    scenario_y_data: Dict[str, Dict[str, List]] = {}

    lead_times_seconds: List[float] = []

    for run_id, run_snaps in sorted(runs_map.items()):
        service.reset_history()
        run_snaps_sorted = sorted(run_snaps, key=lambda x: x.step_index)
        scn_name = run_snaps_sorted[0].scenario

        if scn_name not in scenario_y_data:
            scenario_y_data[scn_name] = {"y_true": [], "y_pred": [], "y_scores": []}

        for snap in run_snaps_sorted:
            batch_res = service.predict_factory_snapshot(
                factory_state=snap.to_dict(),
                ground_truth_events=snap.ground_truth_failure_times,
            )

            for st_id, pred in batch_res.predictions.items():
                is_gt_anomaly = snap.ground_truth_anomalies.get(st_id, False)
                y_t = 1 if is_gt_anomaly else 0
                y_p = 1 if pred.detected else 0
                y_s = pred.anomaly_score

                all_y_true.append(y_t)
                all_y_pred.append(y_p)
                all_y_scores.append(y_s)

                scenario_y_data[scn_name]["y_true"].append(y_t)
                scenario_y_data[scn_name]["y_pred"].append(y_p)
                scenario_y_data[scn_name]["y_scores"].append(y_s)

                if pred.lead_time_if_known is not None and is_gt_anomaly:
                    lead_times_seconds.append(pred.lead_time_if_known)

    # Compute overall metrics
    overall_metrics = calculate_metrics(all_y_true, all_y_pred, all_y_scores)
    mean_lead_time_sec = float(np.mean(lead_times_seconds)) if lead_times_seconds else 0.0
    overall_metrics["mean_lead_time_seconds"] = round(mean_lead_time_sec, 2)
    overall_metrics["mean_lead_time_minutes"] = round(mean_lead_time_sec / 60.0, 2)

    # Compute per-scenario metrics
    for scn_name, data_dict in scenario_y_data.items():
        scenario_metrics[scn_name] = calculate_metrics(
            data_dict["y_true"],
            data_dict["y_pred"],
            data_dict["y_scores"],
        )

    return {
        "model_name": model_name,
        "overall": overall_metrics,
        "scenarios": scenario_metrics,
        "lead_times_recorded": len(lead_times_seconds),
    }


def run_comprehensive_evaluation(
    model_dir: str = DEFAULT_MODEL_DIR,
    random_seed: int = 42,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Loads saved models and runs evaluation across all 5 test scenarios.
    """
    if verbose:
        print("=" * 75)
        print("PHASE 4: ML ANOMALY DETECTION EVALUATION BENCHMARK")
        print("=" * 75)

    # 1. Load artifacts
    scaler = FeatureScaler.load(os.path.join(model_dir, "scaler.json"))
    if_model = IsolationForestAnomalyModel.load(model_dir)
    lstm_model = LSTMAutoencoderModel.load(model_dir)

    # 2. Generate dataset
    dataset = generate_full_factory_dataset(
        n_train_runs=6,
        n_val_runs=2,
        steps_per_run=50,
        random_seed=random_seed,
    )
    baseline = calculate_baseline([s.to_dict() for s in dataset["train"]])
    test_snaps = dataset["test"]

    if verbose:
        print(f"Loaded models from: {model_dir}")
        print(f"Evaluating across {len(test_snaps)} test snapshots over 5 scenarios...")

    # 3. Evaluate Model A: Isolation Forest
    if_results = evaluate_model_on_test_runs(
        model=if_model,
        test_snapshots=test_snaps,
        scaler=scaler,
        baseline=baseline,
        model_name="Isolation Forest (Model A)",
    )

    # 4. Evaluate Model B: LSTM Autoencoder
    lstm_results = evaluate_model_on_test_runs(
        model=lstm_model,
        test_snapshots=test_snaps,
        scaler=scaler,
        baseline=baseline,
        model_name="LSTM Autoencoder (Model B)",
    )

    # 5. Display comparison table
    if verbose:
        print("\n" + "=" * 75)
        print("BENCHMARK RESULTS: OVERALL PERFORMANCE COMPARISON")
        print("=" * 75)
        print(f"{'Metric':<25} {'Isolation Forest (A)':<22} {'LSTM Autoencoder (B)':<22}")
        print("-" * 75)
        metrics_keys = [
            ("Precision", "precision"),
            ("Recall", "recall"),
            ("F1 Score", "f1"),
            ("ROC-AUC", "roc_auc"),
            ("PR-AUC", "pr_auc"),
            ("False Positive Rate", "false_positive_rate"),
            ("Mean Lead Time (min)", "mean_lead_time_minutes"),
        ]
        for label, key in metrics_keys:
            val_if = if_results["overall"].get(key, 0.0)
            val_lstm = lstm_results["overall"].get(key, 0.0)
            print(f"{label:<25} {val_if:<22} {val_lstm:<22}")

        print("\n" + "=" * 75)
        print("PER-SCENARIO F1 SCORE BREAKDOWN")
        print("=" * 75)
        print(f"{'Scenario':<30} {'Isolation Forest F1':<22} {'LSTM Autoencoder F1':<22}")
        print("-" * 75)
        all_scenarios = sorted(set(list(if_results["scenarios"].keys()) + list(lstm_results["scenarios"].keys())))
        for scn in all_scenarios:
            f1_if = if_results["scenarios"].get(scn, {}).get("f1", 0.0)
            f1_lstm = lstm_results["scenarios"].get(scn, {}).get("f1", 0.0)
            print(f"{scn:<30} {f1_if:<22.4f} {f1_lstm:<22.4f}")

    benchmark_summary = {
        "timestamp": time.time(),
        "isolation_forest": if_results,
        "lstm_autoencoder": lstm_results,
    }

    eval_out_path = os.path.join(model_dir, "evaluation_results.json")
    with open(eval_out_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_summary, f, indent=2)

    return benchmark_summary


if __name__ == "__main__":
    run_comprehensive_evaluation()
