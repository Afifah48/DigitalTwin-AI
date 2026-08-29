import os
import argparse
import pandas as pd
import numpy as np


def generate_dataset_report(data_dir: str = "data"):
    episodes_path = os.path.join(data_dir, "episodes.parquet")
    telemetry_path = os.path.join(data_dir, "station_telemetry.parquet")
    quality_path = os.path.join(data_dir, "vehicle_quality.parquet")
    bottleneck_path = os.path.join(data_dir, "bottleneck_targets.parquet")

    if not os.path.exists(episodes_path):
        print(f"Error: dataset not found at {data_dir}. Run generator first.")
        return

    episodes_df = pd.read_parquet(episodes_path)
    telemetry_df = pd.read_parquet(telemetry_path)
    quality_df = pd.read_parquet(quality_path)
    bottleneck_df = pd.read_parquet(bottleneck_path)

    print("=" * 80)
    print(" AUTOMOTIVE PRODUCTION DIGITAL TWIN - PHASE 2 DATASET STATISTICAL REPORT")
    print("=" * 80)

    print(f"Total Episodes:             {len(episodes_df):,}")
    print(f"Total Station Observations: {len(telemetry_df):,}")
    print(f"Total Completed Vehicles:   {len(quality_df):,}")
    print(f"Total Bottleneck Queries:   {len(bottleneck_df):,}")
    print(f"Total Discrete Events:      {episodes_df['total_events'].sum():,}")

    print("\n" + "-" * 80)
    print(" SCENARIO DISTRIBUTION")
    print("-" * 80)
    sc_counts = episodes_df["scenario_type"].value_counts()
    for sc, cnt in sc_counts.items():
        print(f"  {sc:<32} {cnt:4d} ({cnt/len(episodes_df)*100:5.1f}%)")

    print("\n" + "-" * 80)
    print(" SPLIT DISTRIBUTION")
    print("-" * 80)
    split_counts = episodes_df["split"].value_counts()
    for sp, cnt in split_counts.items():
        print(f"  {sp:<12} {cnt:4d} episodes ({cnt/len(episodes_df)*100:5.1f}%)")

    print("\n" + "-" * 80)
    print(" MACHINE STATE DISTRIBUTION")
    print("-" * 80)
    state_counts = telemetry_df["machine_state"].value_counts()
    for st, cnt in state_counts.items():
        print(f"  {st:<20} {cnt:6d} snapshots ({cnt/len(telemetry_df)*100:5.2f}%)")

    print("\n" + "-" * 80)
    print(" BOTTLENECK & CONSTRAINT LABELS")
    print("-" * 80)
    b_counts = bottleneck_df["bottleneck_in_horizon"].value_counts()
    b_true = b_counts.get(True, 0)
    b_false = b_counts.get(False, 0)
    print(f"  Bottleneck in Future 20m:  {b_true:,} positive ({b_true/len(bottleneck_df)*100:5.1f}%), {b_false:,} negative ({b_false/len(bottleneck_df)*100:5.1f}%)")

    sev_counts = bottleneck_df[bottleneck_df["bottleneck_in_horizon"]]["bottleneck_severity"].value_counts()
    for sev, cnt in sev_counts.items():
        print(f"    - Severity {sev:<10}   {cnt:5d} ({cnt/max(1, b_true)*100:5.1f}%)")

    print("\n" + "-" * 80)
    print(" VEHICLE QUALITY & DEFECT DISTRIBUTION")
    print("-" * 80)
    def_counts = quality_df["is_defective"].value_counts()
    d_true = def_counts.get(True, 0)
    print(f"  Defective Vehicles:        {d_true:,} ({d_true/len(quality_df)*100:5.2f}%)")
    cat_counts = quality_df[quality_df["is_defective"]]["defect_category"].value_counts()
    for cat, cnt in cat_counts.items():
        print(f"    - Category {cat:<20} {cnt:4d} ({cnt/max(1, d_true)*100:5.1f}%)")

    print("\n" + "-" * 80)
    print(" TELEMETRY OBSERVATION PERCENTAGES")
    print("-" * 80)
    blocked_pct = (telemetry_df["is_blocked"] == 1).mean() * 100.0
    starved_pct = (telemetry_df["is_starved"] == 1).mean() * 100.0
    down_pct = (telemetry_df["is_down"] == 1).mean() * 100.0
    missing_pct = telemetry_df["sensor_missing_flag"].mean() * 100.0

    print(f"  Blocked Snapshots:         {blocked_pct:5.2f}%")
    print(f"  Starved Snapshots:         {starved_pct:5.2f}%")
    print(f"  Downtime Snapshots:        {down_pct:5.2f}%")
    print(f"  Sensor Missing Snapshots:  {missing_pct:5.2f}%")

    print("\n" + "-" * 80)
    print(" PHYSICAL PROCESS DISTRIBUTIONS (MEAN ± STD)")
    print("-" * 80)
    print(f"  Cycle Time:                {telemetry_df['cycle_time'].mean():.2f}s ± {telemetry_df['cycle_time'].std():.2f}s")
    print(f"  Queue Length:              {telemetry_df['queue_length'].mean():.2f} ± {telemetry_df['queue_length'].std():.2f} vehicles")
    print(f"  Buffer Occupancy:          {telemetry_df['buffer_occupancy'].mean():.2f} ± {telemetry_df['buffer_occupancy'].std():.2f} (Cap: 5)")
    print(f"  Station Utilization:       {telemetry_df['utilization'].mean():.1f}% ± {telemetry_df['utilization'].std():.1f}%")
    print(f"  Factory Throughput UPH:    {episodes_df['throughput_uph'].mean():.1f} ± {episodes_df['throughput_uph'].std():.1f} UPH")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Dataset Statistical Report Generator")
    parser.add_argument("--data-dir", "-d", type=str, default="data", help="Directory containing parquet datasets")
    args = parser.parse_args()
    generate_dataset_report(args.data_dir)


if __name__ == "__main__":
    main()
