import os
import argparse
from typing import Dict, List, Any, Optional
from collections import defaultdict
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
)

from ..models.enums import StationId
from .pipeline import BottleneckPipeline


class OfflineEvaluator:
    """
    High-Performance Offline Evaluation Engine for Phase 5 Bottleneck Prediction.
    Evaluates predictions against Phase 2 ground-truth bottleneck targets.
    """

    def __init__(self, pipeline: Optional[BottleneckPipeline] = None):
        self.pipeline = pipeline or BottleneckPipeline()

    def evaluate_dataset(
        self,
        data_dir: str = "data",
        decision_threshold: float = 0.38,
    ) -> Dict[str, Any]:
        telemetry_path = os.path.join(data_dir, "station_telemetry.parquet")
        targets_path = os.path.join(data_dir, "bottleneck_targets.parquet")
        episodes_path = os.path.join(data_dir, "episodes.parquet")

        if not os.path.exists(telemetry_path) or not os.path.exists(targets_path):
            raise FileNotFoundError(f"Parquet files not found in {data_dir}.")

        telemetry_df = pd.read_parquet(telemetry_path)
        targets_df = pd.read_parquet(targets_path)
        episodes_df = pd.read_parquet(episodes_path) if os.path.exists(episodes_path) else None

        # Build episode scenario mapping
        ep_scenarios = {}
        if episodes_df is not None:
            for _, r in episodes_df.iterrows():
                ep_scenarios[r["episode_id"]] = r["scenario_type"]

        # Merge telemetry and targets
        merged_df = pd.merge(
            telemetry_df,
            targets_df,
            on=["episode_id", "timestamp", "station_id"],
            how="inner",
            suffixes=("", "_target"),
        )

        all_y_true = []
        all_y_scores = []
        all_y_pred = []
        lead_times = []
        ttb_errors = []

        scenario_evals: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: {"y_true": [], "y_score": []})
        station_evals: Dict[str, Dict[str, List[float]]] = {st.value: {"y_true": [], "y_score": []} for st in StationId}

        # Index records into nested dict: data_tree[ep_id][timestamp][station_id] = record
        data_tree: Dict[str, Dict[float, Dict[str, Dict[str, Any]]]] = defaultdict(lambda: defaultdict(dict))
        for row in merged_df.to_dict(orient="records"):
            data_tree[row["episode_id"]][row["timestamp"]][row["station_id"]] = row

        episodes = list(data_tree.keys())
        print(f"Running Phase 5 offline evaluation across {len(episodes)} episodes...")

        for ep_id in episodes:
            sc_type = ep_scenarios.get(ep_id, "UNKNOWN")
            self.pipeline.reset()
            ep_time_dict = data_tree[ep_id]

            for t in sorted(ep_time_dict.keys()):
                st_dict = ep_time_dict[t]
                station_tels: Dict[StationId, Dict[str, Any]] = {}
                for st_val, row_dict in st_dict.items():
                    st_id = StationId(st_val) if isinstance(st_val, str) else st_val
                    station_tels[st_id] = row_dict

                analysis = self.pipeline.analyze_snapshot(t, station_tels)

                for st_risk in analysis.station_ranking:
                    st_id_str = st_risk.station_id.value
                    target_row = st_dict.get(st_id_str)
                    if target_row is None:
                        continue

                    y_true = 1 if target_row["bottleneck_in_horizon"] else 0
                    y_score = st_risk.risk_score
                    y_pred = 1 if y_score >= decision_threshold else 0

                    all_y_true.append(y_true)
                    all_y_scores.append(y_score)
                    all_y_pred.append(y_pred)

                    scenario_evals[sc_type]["y_true"].append(y_true)
                    scenario_evals[sc_type]["y_score"].append(y_score)

                    station_evals[st_id_str]["y_true"].append(y_true)
                    station_evals[st_id_str]["y_score"].append(y_score)

                    # Compute lead time if true onset exists and model detected
                    if y_true == 1 and y_pred == 1 and pd.notna(target_row["bottleneck_onset_time"]):
                        lead = target_row["bottleneck_onset_time"] - t
                        if lead >= 0:
                            lead_times.append(lead)

                    # Evaluate time-to-bottleneck error
                    if y_true == 1 and pd.notna(target_row.get("time_to_bottleneck")) and st_risk.time_to_bottleneck_seconds is not None:
                        gt_ttb = float(target_row["time_to_bottleneck"])
                        pred_ttb = float(st_risk.time_to_bottleneck_seconds)
                        ttb_errors.append(abs(pred_ttb - gt_ttb))

        y_true_arr = np.array(all_y_true)
        y_score_arr = np.array(all_y_scores)
        y_pred_arr = np.array(all_y_pred)

        # Global Metrics
        prec = precision_score(y_true_arr, y_pred_arr, zero_division=0)
        rec = recall_score(y_true_arr, y_pred_arr, zero_division=0)
        f1 = f1_score(y_true_arr, y_pred_arr, zero_division=0)
        roc_auc = roc_auc_score(y_true_arr, y_score_arr) if len(np.unique(y_true_arr)) > 1 else 1.0
        pr_auc = average_precision_score(y_true_arr, y_score_arr) if len(np.unique(y_true_arr)) > 1 else 1.0

        tn, fp, fn, tp = confusion_matrix(y_true_arr, y_pred_arr).ravel()
        fpr = fp / max(1, fp + tn)
        mean_lead_time_s = float(np.mean(lead_times)) if lead_times else 0.0
        mean_ttb_mae_s = float(np.mean(ttb_errors)) if ttb_errors else 0.0

        # Scenario breakdowns
        sc_metrics = {}
        for sc, data in scenario_evals.items():
            sc_yt = np.array(data["y_true"])
            sc_ys = np.array(data["y_score"])
            sc_yp = (sc_ys >= decision_threshold).astype(int)
            sc_metrics[sc] = {
                "precision": round(float(precision_score(sc_yt, sc_yp, zero_division=0)), 4),
                "recall": round(float(recall_score(sc_yt, sc_yp, zero_division=0)), 4),
                "f1": round(float(f1_score(sc_yt, sc_yp, zero_division=0)), 4),
                "roc_auc": round(float(roc_auc_score(sc_yt, sc_ys)), 4) if len(np.unique(sc_yt)) > 1 else 1.0,
                "samples": len(sc_yt),
            }

        # Station breakdowns
        st_metrics = {}
        for st, data in station_evals.items():
            st_yt = np.array(data["y_true"])
            st_ys = np.array(data["y_score"])
            st_yp = (st_ys >= decision_threshold).astype(int)
            st_metrics[st] = {
                "precision": round(float(precision_score(st_yt, st_yp, zero_division=0)), 4),
                "recall": round(float(recall_score(st_yt, st_yp, zero_division=0)), 4),
                "f1": round(float(f1_score(st_yt, st_yp, zero_division=0)), 4),
                "samples": len(st_yt),
            }

        results = {
            "total_observations": len(y_true_arr),
            "decision_threshold": decision_threshold,
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1": round(float(f1), 4),
            "roc_auc": round(float(roc_auc), 4),
            "pr_auc": round(float(pr_auc), 4),
            "fpr": round(float(fpr), 4),
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
            "mean_detection_lead_time_seconds": round(mean_lead_time_s, 1),
            "mean_detection_lead_time_minutes": round(mean_lead_time_s / 60.0, 2),
            "time_to_bottleneck_mae_seconds": round(mean_ttb_mae_s, 1),
            "scenario_metrics": sc_metrics,
            "station_metrics": st_metrics,
        }

        self._print_evaluation_report(results)
        return results

    def _print_evaluation_report(self, results: Dict[str, Any]):
        print("\n" + "=" * 80)
        print(" PHASE 5 BOTTLENECK PREDICTION - OFFLINE EVALUATION REPORT")
        print("=" * 80)
        print(f"Total Observations Evaluated: {results['total_observations']:,}")
        print(f"Decision Threshold:           {results['decision_threshold']:.2f}")
        print(f"Precision:                    {results['precision']:.4f} ({results['precision']*100:.1f}%)")
        print(f"Recall:                       {results['recall']:.4f} ({results['recall']*100:.1f}%)")
        print(f"F1-Score:                     {results['f1']:.4f}")
        print(f"ROC-AUC:                      {results['roc_auc']:.4f}")
        print(f"PR-AUC:                       {results['pr_auc']:.4f}")
        print(f"False Positive Rate (FPR):    {results['fpr']:.4f} ({results['fpr']*100:.2f}%)")
        print(f"Mean Detection Lead Time:     {results['mean_detection_lead_time_seconds']:.1f}s ({results['mean_detection_lead_time_minutes']:.1f} min)")
        print(f"Time-to-Bottleneck MAE:       {results['time_to_bottleneck_mae_seconds']:.1f}s")

        cm = results["confusion_matrix"]
        print("\n" + "-" * 80)
        print(" CONFUSION MATRIX")
        print("-" * 80)
        print(f"  True Negatives (TN):  {cm['tn']:,} | False Positives (FP): {cm['fp']:,}")
        print(f"  False Negatives (FN): {cm['fn']:,} | True Positives (TP):  {cm['tp']:,}")

        print("\n" + "-" * 80)
        print(" SCENARIO BREAKDOWN")
        print("-" * 80)
        print(f"{'Scenario Type':<32} {'Samples':<10} {'Precision':<12} {'Recall':<10} {'F1-Score':<10} {'ROC-AUC':<10}")
        print("-" * 80)
        for sc, m in results["scenario_metrics"].items():
            print(f"{sc:<32} {m['samples']:<10} {m['precision']:<12.4f} {m['recall']:<10.4f} {m['f1']:<10.4f} {m['roc_auc']:<10.4f}")

        print("\n" + "-" * 80)
        print(" STATION-LEVEL BREAKDOWN")
        print("-" * 80)
        print(f"{'Station':<10} {'Samples':<10} {'Precision':<12} {'Recall':<10} {'F1-Score':<10}")
        print("-" * 80)
        for st, m in results["station_metrics"].items():
            print(f"{st:<10} {m['samples']:<10} {m['precision']:<12.4f} {m['recall']:<10.4f} {m['f1']:<10.4f}")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Phase 5 Offline Bottleneck Evaluator")
    parser.add_argument("--data-dir", "-d", type=str, default="data", help="Directory containing parquet datasets")
    parser.add_argument("--threshold", "-t", type=float, default=0.38, help="Decision threshold for binary classification")
    args = parser.parse_args()

    evaluator = OfflineEvaluator()
    evaluator.evaluate_dataset(args.data_dir, decision_threshold=args.threshold)


if __name__ == "__main__":
    main()

