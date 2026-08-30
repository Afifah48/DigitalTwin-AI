"""
Phase 6 Validation: Data Adapter & Evaluation Script

Maps vehicle_station_history.parquet → VehicleObservation schema using
semantically correct field derivations, then evaluates QualityRiskService
against vehicle_quality.parquet ground truth (test split only).

Does NOT modify: model weights, ground-truth labels, calibration artifacts,
feature definitions, or any Phase 1–9 code.
"""
import sys
import warnings
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import (
    roc_auc_score, precision_recall_curve, auc,
    precision_score, recall_score, f1_score,
    confusion_matrix, average_precision_score,
)

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.quality.schemas import VehicleObservation
from backend.quality.service import QualityRiskService
from backend.quality.phase4_adapter import Phase4Adapter
from backend.quality.phase5_adapter import Phase5Adapter

DATA_DIR = ROOT / "data"
HISTORY_FILE = DATA_DIR / "vehicle_station_history.parquet"
QUALITY_FILE = DATA_DIR / "vehicle_quality.parquet"
PHASE45_FILE = DATA_DIR / "phase4_phase5_integration.parquet"
MODELS_DIR = ROOT / "backend" / "models" / "quality"

# --- Model name mapping ---
MODEL_MAP = {
    "HORIZON CROSS": "SUV",
    "NEXUS SEDAN":   "Sedan",
    "VALENCE SUV":   "SUV",
    "APEX GT-EV":    "Coupe",
}

def derive_observation(row: pd.Series) -> VehicleObservation:
    """Map a single vehicle_station_history row into VehicleObservation."""
    station_id = str(row["station_id"])
    cycle_time = float(row["actual_cycle_time"])
    deviation = float(row["deviation_at_pass"])

    raw_model = str(row.get("model", "NEXUS SEDAN"))
    vehicle_model = MODEL_MAP.get(raw_model, "Sedan")

    td = row.get("thermal_delta")
    temperature = 62.0 + (float(td) if pd.notna(td) else 0.0)

    tv = row.get("torque_variance")
    current_variance = float(tv) if pd.notna(tv) else 0.05

    vibration = min(0.5, 0.05 + abs(deviation) * 0.8)

    expected_ct = float(row.get("expected_cycle_time", 52.0))
    motor_current = 4.8 * (cycle_time / max(expected_ct, 1.0))

    exposure = str(row.get("exposure_flag", "LOW"))
    if exposure == "HIGH":
        machine_state = "WARNING"
    elif exposure == "MEDIUM":
        machine_state = "BLOCKED"
    else:
        machine_state = "RUNNING"

    queue_length = max(0, int(deviation * 30))
    buffer_occupancy = max(0.0, min(10.0, 3.0 + deviation * 20))

    return VehicleObservation(
        vehicle_id=str(row["vehicle_id"]),
        station_id=station_id,
        timestamp=float(row["entered_at"]),
        vehicle_model=vehicle_model,
        vehicle_variant="Base",
        duration=cycle_time,
        cycle_time=cycle_time,
        cycle_time_delta=deviation,
        queue_length=queue_length,
        buffer_occupancy=buffer_occupancy,
        temperature=temperature,
        vibration=vibration,
        motor_current=motor_current,
        current_variance=current_variance,
        machine_state=machine_state,
        torque=None,
    )

def main():
    print("Loading datasets...")
    df_hist = pd.read_parquet(HISTORY_FILE)
    df_qual = pd.read_parquet(QUALITY_FILE)

    df_qual_test = df_qual[df_qual["split"] == "test"].copy()
    test_vids = set(df_qual_test["vehicle_id"].unique())
    df_hist_test = df_hist[df_hist["vehicle_id"].isin(test_vids)].copy()

    p4_adapter = Phase4Adapter()
    p5_adapter = Phase5Adapter()

    has_p45 = False
    if PHASE45_FILE.exists():
        print("Loading Phase 4/5 integration data...")
        df_p45 = pd.read_parquet(PHASE45_FILE)
        for _, row in df_p45.iterrows():
            d = row.to_dict()
            try:
                p4_adapter.ingest_prediction(d)
                p5_adapter.ingest_snapshot(d)
                has_p45 = True
            except Exception:
                pass

    print("Loading original QualityRiskService model...")
    service = QualityRiskService().load_artifacts(str(MODELS_DIR), model_type="xgboost")

    print("Running predictions on TEST split...")
    history_groups = df_hist_test.groupby("vehicle_id")

    y_true = []
    y_prob = []
    y_sev = []
    
    count = 0
    for i, (_, qrow) in enumerate(df_qual_test.iterrows()):
        vid = qrow["vehicle_id"]
        if vid not in history_groups.groups:
            continue

        v_hist = history_groups.get_group(vid).sort_values("entered_at")
        observations = [derive_observation(r) for _, r in v_hist.iterrows()]
        as_of_ts = float(v_hist["completed_at"].max())

        pred = service.predict(
            vehicle_id=vid,
            vehicle_history=observations,
            as_of_timestamp=as_of_ts,
            phase4_adapter=p4_adapter,
            phase5_adapter=p5_adapter,
        )

        y_true.append(int(qrow["is_defective"]))
        y_prob.append(pred.defect_probability)
        y_sev.append(qrow.get("defect_severity", "NONE"))
        
        count += 1
        if count % 200 == 0:
            print(f"Processed {count}/{len(df_qual_test)} vehicles...")

    y_true = np.array(y_true, dtype=int)
    y_prob = np.array(y_prob, dtype=float)
    y_pred = (y_prob >= 0.5).astype(int)

    n_unique = len(np.unique(y_prob))
    non_constant = n_unique > 1

    if len(np.unique(y_true)) > 1 and non_constant:
        roc = roc_auc_score(y_true, y_prob)
        p_curve, r_curve, _ = precision_recall_curve(y_true, y_prob)
        pr_auc_val = auc(r_curve, p_curve)
    else:
        roc = float("nan")
        pr_auc_val = float("nan")

    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    # High severity recall
    high_sev_mask = [s in ("HIGH", "CRITICAL") for s in y_sev]
    if any(high_sev_mask):
        high_sev_true = np.array([y_true[i] for i, m in enumerate(high_sev_mask) if m])
        high_sev_pred = np.array([y_pred[i] for i, m in enumerate(high_sev_mask) if m])
        if len(high_sev_true) > 0 and sum(high_sev_true) > 0:
            high_sev_recall = recall_score(high_sev_true, high_sev_pred, zero_division=0)
        else:
            high_sev_recall = float("nan")
    else:
        high_sev_recall = float("nan")

    print("\n================ REPORT ================")
    print(f"test vehicles: {len(y_true)}")
    print(f"defective: {sum(y_true)}")
    print(f"ROC-AUC: {roc:.4f}")
    print(f"PR-AUC: {pr_auc_val:.4f}")
    print(f"precision: {prec:.4f}")
    print(f"recall: {rec:.4f}")
    print(f"F1: {f1:.4f}")
    print(f"high-severity recall: {high_sev_recall:.4f}")
    print(f"constant prediction: {'YES' if not non_constant else 'NO'} ({n_unique} unique)")
    print(f"Phase 4 features active: {'YES' if has_p45 else 'NO'}")
    print(f"Phase 5 features active: {'YES' if has_p45 else 'NO'}")
    
    # Optional prediction distribution
    print("\nPrediction distribution:")
    for label, name in [(0, "Non-defective"), (1, "Defective")]:
        mask = y_true == label
        if mask.sum() > 0:
            probs = y_prob[mask]
            print(f"  {name}: mean={probs.mean():.4f}, std={probs.std():.4f}, min={probs.min():.4f}, max={probs.max():.4f}")

if __name__ == "__main__":
    main()
