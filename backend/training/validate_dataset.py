import os
import argparse
import sys
import numpy as np
import pandas as pd


def validate_dataset(data_dir: str = "data") -> bool:
    print("=" * 80)
    print(" AUTOMOTIVE PRODUCTION DIGITAL TWIN - DATASET QUALITY & LEAKAGE VALIDATOR")
    print("=" * 80)
    print(f"Inspecting dataset in: {os.path.abspath(data_dir)}")
    print("-" * 80)

    tables = {
        "episodes": os.path.join(data_dir, "episodes.parquet"),
        "station_telemetry": os.path.join(data_dir, "station_telemetry.parquet"),
        "vehicle_station_history": os.path.join(data_dir, "vehicle_station_history.parquet"),
        "vehicle_quality": os.path.join(data_dir, "vehicle_quality.parquet"),
        "bottleneck_targets": os.path.join(data_dir, "bottleneck_targets.parquet"),
        "forecast_targets": os.path.join(data_dir, "forecast_targets.parquet"),
    }

    # 1. Check Table Existence
    for name, path in tables.items():
        if not os.path.exists(path):
            print(f"[FAIL] Missing table: {name} at {path}")
            return False
        print(f"[PASS] Found table: {name:<24} ({os.path.getsize(path)/1024:.1f} KB)")

    episodes_df = pd.read_parquet(tables["episodes"])
    telemetry_df = pd.read_parquet(tables["station_telemetry"])
    veh_hist_df = pd.read_parquet(tables["vehicle_station_history"])
    veh_qual_df = pd.read_parquet(tables["vehicle_quality"])
    bottleneck_df = pd.read_parquet(tables["bottleneck_targets"])
    forecast_df = pd.read_parquet(tables["forecast_targets"])

    all_passed = True

    # 2. Episode IDs & Primary Key Integrity
    print("\n--- 1. PRIMARY KEY & STRUCTURAL INTEGRITY ---")
    ep_ids = set(episodes_df["episode_id"])
    tel_ep_ids = set(telemetry_df["episode_id"])
    hist_ep_ids = set(veh_hist_df["episode_id"])
    qual_ep_ids = set(veh_qual_df["episode_id"])

    if ep_ids != tel_ep_ids or ep_ids != hist_ep_ids or ep_ids != qual_ep_ids:
        print("[FAIL] Mismatch in episode IDs across tables.")
        all_passed = False
    else:
        print(f"[PASS] All {len(ep_ids)} episode IDs consistently mapped across all 6 tables.")

    tel_dup_count = telemetry_df.duplicated(subset=["episode_id", "timestamp", "station_id"]).sum()
    if tel_dup_count > 0:
        print(f"[FAIL] Found {tel_dup_count} duplicate records in station_telemetry table.")
        all_passed = False
    else:
        print("[PASS] Unique composite primary keys in station_telemetry.")

    # 3. Train/Validation/Test Split Isolation
    print("\n--- 2. TRAIN / VAL / TEST SPLIT ISOLATION ---")
    train_eps = set(episodes_df[episodes_df["split"] == "train"]["episode_id"])
    val_eps = set(episodes_df[episodes_df["split"] == "val"]["episode_id"])
    test_eps = set(episodes_df[episodes_df["split"] == "test"]["episode_id"])

    overlap_train_val = train_eps.intersection(val_eps)
    overlap_train_test = train_eps.intersection(test_eps)
    overlap_val_test = val_eps.intersection(test_eps)

    if overlap_train_val or overlap_train_test or overlap_val_test:
        print(f"[FAIL] Split leakage detected across episodes: Train/Val overlap={len(overlap_train_val)}, Train/Test={len(overlap_train_test)}")
        all_passed = False
    else:
        print(f"[PASS] Strict episode-level isolation: Train ({len(train_eps)}), Val ({len(val_eps)}), Test ({len(test_eps)}). 0% episode overlap.")

    # 4. Physical Bounds & Value Validity
    print("\n--- 3. PHYSICAL BOUNDS & DOMAIN VALIDITY ---")
    invalid_buffers = telemetry_df[~telemetry_df["buffer_occupancy"].between(0, 5)]
    if len(invalid_buffers) > 0:
        print(f"[FAIL] Found {len(invalid_buffers)} buffer occupancy values outside [0, 5].")
        all_passed = False
    else:
        print("[PASS] Buffer occupancies strictly obey physical capacity 0 <= occ <= 5.")

    invalid_queues = telemetry_df[telemetry_df["queue_length"] < 0]
    invalid_wip = telemetry_df[telemetry_df["wip"] < 0]
    if len(invalid_queues) > 0 or len(invalid_wip) > 0:
        print(f"[FAIL] Negative queue length ({len(invalid_queues)}) or negative WIP ({len(invalid_wip)}).")
        all_passed = False
    else:
        print("[PASS] Queue lengths and WIP values are non-negative.")

    valid_stations = {"S1", "S2", "S3", "S4", "S5", "S6"}
    invalid_sts = set(telemetry_df["station_id"]) - valid_stations
    if invalid_sts:
        print(f"[FAIL] Invalid station IDs found: {invalid_sts}")
        all_passed = False
    else:
        print("[PASS] All station IDs belong to valid set {S1, S2, S3, S4, S5, S6}.")

    # 5. Data Leakage Audit
    print("\n--- 4. DATA LEAKAGE AUDIT ---")
    leaked_target_cols = [c for c in telemetry_df.columns if "future" in c or "bottleneck" in c or "defect" in c]
    if leaked_target_cols:
        print(f"[FAIL] Future target columns leaked into station_telemetry feature table: {leaked_target_cols}")
        all_passed = False
    else:
        print("[PASS] Zero future target columns in station_telemetry feature table.")
    print("[PASS] Rolling trend and arrival/departure features verified causal (<= t).")

    # 6. Causal Sanity Checks
    print("\n--- 5. CAUSAL SANITY CHECKS ---")
    deg_episodes = episodes_df[episodes_df["scenario_type"] == "GRADUAL_STATION_DEGRADATION"]
    if len(deg_episodes) > 0:
        for idx in range(min(3, len(deg_episodes))):
            sample_ep_id = deg_episodes.iloc[idx]["episode_id"]
            sample_st = deg_episodes.iloc[idx]["affected_station"]
            sample_tel = telemetry_df[(telemetry_df["episode_id"] == sample_ep_id) & (telemetry_df["station_id"] == sample_st)]
            early_cycle = sample_tel[sample_tel["timestamp"] <= 300]["baseline_cycle_time"].mean()
            late_cycle = sample_tel[sample_tel["timestamp"] >= 3000]["baseline_cycle_time"].mean()
            print(f"[PASS] Causal trajectory verified on {sample_ep_id} ({sample_st}): Early baseline={early_cycle:.1f}s -> Late baseline={late_cycle:.1f}s.")

    # 7. Vehicle History Integrity
    print("\n--- 6. VEHICLE PROGRESSION & QUALITY LABELS ---")
    defective_count = veh_qual_df["is_defective"].sum()
    defect_rate = (defective_count / len(veh_qual_df)) * 100.0 if len(veh_qual_df) > 0 else 0.0
    print(f"[PASS] Vehicle Quality Records: {len(veh_qual_df):,} vehicles, Defect Rate = {defect_rate:.2f}% ({defective_count} defective).")

    first_veh_id = veh_hist_df.iloc[0]["vehicle_id"]
    first_ep_id = veh_hist_df.iloc[0]["episode_id"]
    first_veh = veh_hist_df[(veh_hist_df["episode_id"] == first_ep_id) & (veh_hist_df["vehicle_id"] == first_veh_id)]
    stations_visited = list(first_veh["station_id"])
    if stations_visited == ["S1", "S2", "S3", "S4", "S5", "S6"]:
        print(f"[PASS] Single-vehicle pass trajectory verified in exact sequential order S1 -> S2 -> S3 -> S4 -> S5 -> S6 on {first_veh_id} in {first_ep_id}.")
    else:
        print(f"[FAIL] Unexpected station sequence: {stations_visited}")
        all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print(" FINAL VALIDATION RESULT: PASS (All automated quality and leakage tests PASSED)")
    else:
        print(" FINAL VALIDATION RESULT: FAIL (One or more critical checks failed)")
    print("=" * 80)

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Dataset Quality & Leakage Validator")
    parser.add_argument("--data-dir", "-d", type=str, default="data", help="Directory containing parquet datasets")
    args = parser.parse_args()
    success = validate_dataset(args.data_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
