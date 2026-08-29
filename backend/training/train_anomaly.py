"""
Training Pipeline for Phase 4 ML Anomaly Detectors.

Executes leak-free data preparation, scaler fitting on training runs only,
trains Model A (Isolation Forest) and Model B (LSTM Autoencoder), derives
statistical thresholds from nominal validation runs, and saves artifacts to models/anomaly/.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Tuple
import numpy as np

from backend.analytics.baseline import calculate_baseline
from backend.app.models.anomaly.features import (
    ANOMALY_FEATURE_NAMES,
    FeatureScaler,
    extract_station_features,
)
from backend.app.models.anomaly.isolation_forest import IsolationForestAnomalyModel
from backend.app.models.anomaly.lstm_autoencoder import LSTMAutoencoderModel
from backend.data.synthetic_factory import (
    TelemetrySnapshot,
    generate_full_factory_dataset,
)

DEFAULT_MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models", "anomaly")
)


def prepare_tabular_and_sequence_data(
    snapshots: List[TelemetrySnapshot],
    scaler: Optional[FeatureScaler] = None,
    window_size: int = 15,
    baseline: Optional[Any] = None,
    fit_scaler: bool = False,
) -> Tuple[np.ndarray, np.ndarray, FeatureScaler]:
    """
    Extracts 11-feature vectors and creates rolling temporal windows partitioned per run and station.

    Args:
        snapshots: List of TelemetrySnapshot records.
        scaler: FeatureScaler instance.
        window_size: Sequence window size for LSTM.
        baseline: Pre-computed statistical baseline.
        fit_scaler: If True, fits the scaler on these snapshots (train set only).

    Returns:
        Tuple of (2D snapshot features, 3D sequence windows, FeatureScaler).
    """
    # Group snapshots by run_id
    runs_map: Dict[str, List[TelemetrySnapshot]] = {}
    for s in snapshots:
        runs_map.setdefault(s.run_id, []).append(s)

    all_raw_snapshots: List[np.ndarray] = []

    # Step 1: Collect raw snapshots
    for run_id, run_snaps in sorted(runs_map.items()):
        # Sort by step_index
        run_snaps_sorted = sorted(run_snaps, key=lambda x: x.step_index)
        for snap in run_snaps_sorted:
            # Build buffer occupancy map
            buf_map = {
                b_id: float(b_data["occupancy"]) for b_id, b_data in snap.buffers.items()
            }
            for st_id, st_tel in snap.stations.items():
                conn_buf_occ = 0.0
                for b_id, occ in buf_map.items():
                    if st_id in b_id:
                        conn_buf_occ = max(conn_buf_occ, occ)
                st_base = baseline.get_station(st_id) if baseline else None
                feat = extract_station_features(
                    st_tel,
                    station_baseline=st_base,
                    connected_buffer_occupancy=conn_buf_occ,
                )
                all_raw_snapshots.append(feat)

    raw_2d = np.array(all_raw_snapshots, dtype=np.float32)

    active_scaler = scaler or FeatureScaler()
    if fit_scaler:
        active_scaler.fit(raw_2d)

    scaled_2d = active_scaler.transform(raw_2d)

    # Step 2: Build rolling sequence windows per run and station (strictly without cross-run leakage)
    sequence_windows: List[np.ndarray] = []
    for run_id, run_snaps in sorted(runs_map.items()):
        run_snaps_sorted = sorted(run_snaps, key=lambda x: x.step_index)
        # Separate sequences by station within this run
        station_trajectories: Dict[str, List[np.ndarray]] = {}
        for snap in run_snaps_sorted:
            buf_map = {
                b_id: float(b_data["occupancy"]) for b_id, b_data in snap.buffers.items()
            }
            for st_id, st_tel in snap.stations.items():
                conn_buf_occ = 0.0
                for b_id, occ in buf_map.items():
                    if st_id in b_id:
                        conn_buf_occ = max(conn_buf_occ, occ)
                st_base = baseline.get_station(st_id) if baseline else None
                raw_f = extract_station_features(
                    st_tel,
                    station_baseline=st_base,
                    connected_buffer_occupancy=conn_buf_occ,
                )
                scaled_f = active_scaler.transform(raw_f.reshape(1, -1))[0]
                station_trajectories.setdefault(st_id, []).append(scaled_f)

        # Slice rolling windows
        for st_id, traj in station_trajectories.items():
            n_points = len(traj)
            for start_idx in range(n_points - window_size + 1):
                win = traj[start_idx : start_idx + window_size]
                sequence_windows.append(win)

    scaled_3d = np.array(sequence_windows, dtype=np.float32)
    return scaled_2d, scaled_3d, active_scaler


def train_anomaly_subsystem(
    model_output_dir: str = DEFAULT_MODEL_DIR,
    window_size: int = 15,
    epochs: int = 30,
    random_seed: int = 42,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Executes end-to-end training of Isolation Forest and LSTM Autoencoder.

    Returns:
        Summary dictionary with training results, thresholds, and artifact paths.
    """
    start_time = time.time()
    os.makedirs(model_output_dir, exist_ok=True)

    if verbose:
        print("=" * 75)
        print("PHASE 4: ML ANOMALY DETECTION TRAINING PIPELINE")
        print("=" * 75)
        print(f"Artifact directory: {model_output_dir}")
        print(f"Random seed: {random_seed} | Window size: {window_size} | Epochs: {epochs}")

    # 1. Generate partitioned dataset (runs 1-6 Train, runs 7-8 Val, runs 9-14 Test)
    if verbose:
        print("\n[1/5] Generating multi-run simulation dataset...")
    dataset = generate_full_factory_dataset(
        n_train_runs=6,
        n_val_runs=2,
        steps_per_run=50,
        random_seed=random_seed,
    )

    train_snaps = dataset["train"]
    val_snaps = dataset["val"]
    if verbose:
        print(f"      Train snapshots: {len(train_snaps)} ({len(train_snaps)//50} nominal runs)")
        print(f"      Val snapshots  : {len(val_snaps)} ({len(val_snaps)//50} nominal runs)")

    # 2. Compute reference statistical baseline on training snapshots
    if verbose:
        print("\n[2/5] Establishing baseline on nominal training data...")
    train_dicts = [s.to_dict() for s in train_snaps]
    baseline = calculate_baseline(train_dicts)

    # 3. Fit scaler ONLY on training data and extract features
    if verbose:
        print("\n[3/5] Extracting 11 features and fitting FeatureScaler (leakage-free)...")
    train_2d, train_3d, scaler = prepare_tabular_and_sequence_data(
        snapshots=train_snaps,
        scaler=None,
        window_size=window_size,
        baseline=baseline,
        fit_scaler=True,
    )

    val_2d, val_3d, _ = prepare_tabular_and_sequence_data(
        snapshots=val_snaps,
        scaler=scaler,
        window_size=window_size,
        baseline=baseline,
        fit_scaler=False,
    )

    if verbose:
        print(f"      Train 2D shape: {train_2d.shape} | Train 3D sequence shape: {train_3d.shape}")
        print(f"      Val 2D shape  : {val_2d.shape} | Val 3D sequence shape  : {val_3d.shape}")

    # 4. Train Model A: Isolation Forest
    if verbose:
        print("\n[4/5] Training Model A: Isolation Forest baseline detector...")
    if_model = IsolationForestAnomalyModel(
        n_estimators=100,
        contamination=0.01,
        random_state=random_seed,
    )
    if_model.fit(train_2d, val_X=val_2d)
    if verbose:
        print(f"      Isolation Forest fitted. Calibrated threshold: {if_model.threshold:.4f}")

    # 5. Train Model B: PyTorch LSTM Autoencoder
    if verbose:
        print("\n[5/5] Training Model B: PyTorch LSTM Autoencoder...")
    lstm_model = LSTMAutoencoderModel(
        window_size=window_size,
        input_dim=11,
        hidden_dim=32,
        num_layers=2,
        dropout=0.1,
        learning_rate=1e-3,
        batch_size=32,
        epochs=epochs,
        random_state=random_seed,
    )
    lstm_model.fit(train_3d, val_X=val_3d, verbose=verbose)
    if verbose:
        print(f"      LSTM Autoencoder fitted. Statistical threshold (p99): {lstm_model.threshold:.5f}")
        print(f"      Val error mean: {lstm_model.val_error_mean:.5f}, std: {lstm_model.val_error_std:.5f}")

    # Save artifacts
    scaler.save(os.path.join(model_output_dir, "scaler.json"))
    if_model.save(model_output_dir)
    lstm_model.save(model_output_dir)

    metadata = {
        "pipeline_version": "1.0.0",
        "timestamp": time.time(),
        "random_seed": random_seed,
        "feature_names": ANOMALY_FEATURE_NAMES,
        "n_features": 11,
        "window_size": window_size,
        "train_runs_count": 6,
        "val_runs_count": 2,
        "isolation_forest": if_model.metadata,
        "lstm_autoencoder": lstm_model.metadata,
        "duration_seconds": round(time.time() - start_time, 2),
    }

    with open(os.path.join(model_output_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    if verbose:
        print("\n" + "=" * 75)
        print("Training completed successfully! Saved all models to disk.")
        print("=" * 75)

    return metadata


if __name__ == "__main__":
    train_anomaly_subsystem()
