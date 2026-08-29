import os
import argparse
import time
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from ..twin.digital_twin import DigitalTwin
from ..config.factory_config import get_default_factory_config
from ..scenarios.registry import ScenarioRegistry
from .resampler import TelemetryResampler
from .quality_model import VehicleQualityEngine
from .labeler import GroundTruthLabeler


def generate_dataset(
    num_episodes: int = 100,
    master_seed: int = 42,
    output_dir: str = "data",
    duration_minutes: float = 80.0,  # 60m observation + 20m future horizon
):
    """
    Generates synthetic factory twin datasets partitioned into train/val/test splits.
    """
    os.makedirs(output_dir, exist_ok=True)
    sim_duration_seconds = duration_minutes * 60.0  # 4800.0s

    rng = np.random.default_rng(master_seed)
    resampler = TelemetryResampler(step_seconds=30.0)
    labeler = GroundTruthLabeler(horizon_seconds=1200.0)

    episodes_records = []
    all_telemetry_dfs = []
    all_targets_dfs = []
    all_vehicle_passes = []
    all_vehicle_qualities = []

    print("=" * 80)
    print(" AUTOMOTIVE PRODUCTION DIGITAL TWIN - PHASE 2 DATASET GENERATOR")
    print("=" * 80)
    print(f"Master Seed:        {master_seed}")
    print(f"Total Episodes:     {num_episodes}")
    print(f"Episode Duration:   {duration_minutes:.1f} minutes ({sim_duration_seconds:.0f}s)")
    print(f"Output Directory:   {output_dir}")
    print("-" * 80)

    start_time = time.time()

    for ep_idx in range(num_episodes):
        ep_id = f"EP_{ep_idx+1:04d}"
        ep_seed = int(rng.integers(1, 1_000_000_000))
        ep_rng = np.random.default_rng(ep_seed)

        # 1. Sample scenario from registry
        scenario = ScenarioRegistry.sample_scenario(rng=ep_rng)
        sc_meta = scenario.get_metadata()

        # 2. Instantiate and configure Digital Twin
        config = get_default_factory_config()
        twin = DigitalTwin(config=config, seed=ep_seed)

        # Apply scenario parameter hooks
        scenario.apply(twin.engine)

        # 3. Simulate continuous discrete-event factory line
        state = twin.simulate(sim_duration_seconds)

        # 4. Resample telemetry to 30-second regular intervals
        tel_df = resampler.sample_episode_telemetry(
            engine=twin.engine,
            episode_id=ep_id,
            max_time_seconds=sim_duration_seconds,
            scenario=scenario,
        )

        # 5. Generate ground truth bottleneck and forecast regression targets
        target_df = labeler.compute_bottleneck_and_forecast_targets(
            telemetry_df=tel_df,
            episode_id=ep_id,
        )

        # 6. Evaluate vehicle pass trajectories and quality ground truth
        quality_engine = VehicleQualityEngine(rng=ep_rng)
        for v in state.completed_vehicles:
            # Vehicle quality record
            q_rec = quality_engine.evaluate_vehicle_quality(v, episode_id=ep_id)
            all_vehicle_qualities.append(q_rec.model_dump(mode="json"))

            # Vehicle pass records
            for p in v.history:
                all_vehicle_passes.append({
                    "episode_id": ep_id,
                    "vehicle_id": v.id,
                    "model": v.model.value if hasattr(v.model, "value") else str(v.model),
                    "station_id": p.station_id.value,
                    "entered_at": p.entered_at,
                    "completed_at": p.completed_at,
                    "actual_cycle_time": p.actual_cycle_time,
                    "expected_cycle_time": p.expected_cycle_time,
                    "deviation_at_pass": p.deviation_at_pass,
                    "torque_variance": p.torque_variance,
                    "thermal_delta": p.thermal_delta,
                    "exposure_flag": p.exposure_flag.value if hasattr(p.exposure_flag, "value") else str(p.exposure_flag),
                })

        # 7. Record episode metadata and split assignment
        # Deterministic 70% Train / 15% Val / 15% Test partition by episode index
        split = "train" if (ep_idx % 20 < 14) else ("val" if (ep_idx % 20 < 17) else "test")

        ep_record = {
            "episode_id": ep_id,
            "master_seed": master_seed,
            "episode_seed": ep_seed,
            "split": split,
            "scenario_type": sc_meta["scenario_type"],
            "severity": sc_meta.get("severity", "MEDIUM"),
            "affected_station": sc_meta.get("affected_station"),
            "start_time": sc_meta.get("start_time", 0.0),
            "end_time": sc_meta.get("end_time", sim_duration_seconds),
            "total_throughput": state.total_throughput,
            "throughput_uph": state.throughput_uph,
            "average_cycle_time": state.average_cycle_time,
            "factory_utilization": state.system_utilization,
            "total_events": len(twin.get_events()),
            "description": sc_meta.get("description", ""),
        }
        episodes_records.append(ep_record)
        all_telemetry_dfs.append(tel_df)
        all_targets_dfs.append(target_df)

        if (ep_idx + 1) % max(1, num_episodes // 10) == 0 or (ep_idx + 1) == num_episodes:
            elapsed = time.time() - start_time
            print(f"  Processed {ep_idx+1:3d}/{num_episodes} episodes ({((ep_idx+1)/num_episodes)*100:.0f}%) | Elapsed: {elapsed:.1f}s")

    # Combine dataframes
    episodes_df = pd.DataFrame(episodes_records)
    telemetry_combined_df = pd.concat(all_telemetry_dfs, ignore_index=True)
    targets_combined_df = pd.concat(all_targets_dfs, ignore_index=True)
    vehicle_history_df = pd.DataFrame(all_vehicle_passes)
    vehicle_quality_df = pd.DataFrame(all_vehicle_qualities)

    # Attach split column to all tables for clean partitioning
    split_map = dict(zip(episodes_df["episode_id"], episodes_df["split"]))
    telemetry_combined_df["split"] = telemetry_combined_df["episode_id"].map(split_map)
    targets_combined_df["split"] = targets_combined_df["episode_id"].map(split_map)
    vehicle_history_df["split"] = vehicle_history_df["episode_id"].map(split_map)
    vehicle_quality_df["split"] = vehicle_quality_df["episode_id"].map(split_map)

    # Separate bottleneck vs forecast targets
    bottleneck_cols = ["episode_id", "timestamp", "station_id", "split", "bottleneck_in_horizon", "bottleneck_onset_time", "time_to_bottleneck", "bottleneck_severity"]
    forecast_cols = [c for c in targets_combined_df.columns if c not in ["bottleneck_in_horizon", "bottleneck_onset_time", "time_to_bottleneck", "bottleneck_severity"]]

    bottleneck_df = targets_combined_df[bottleneck_cols]
    forecast_df = targets_combined_df[forecast_cols]

    # Save to Parquet tables
    episodes_path = os.path.join(output_dir, "episodes.parquet")
    tel_path = os.path.join(output_dir, "station_telemetry.parquet")
    veh_hist_path = os.path.join(output_dir, "vehicle_station_history.parquet")
    veh_qual_path = os.path.join(output_dir, "vehicle_quality.parquet")
    bottle_path = os.path.join(output_dir, "bottleneck_targets.parquet")
    forecast_path = os.path.join(output_dir, "forecast_targets.parquet")

    episodes_df.to_parquet(episodes_path, index=False)
    telemetry_combined_df.to_parquet(tel_path, index=False)
    vehicle_history_df.to_parquet(veh_hist_path, index=False)
    vehicle_quality_df.to_parquet(veh_qual_path, index=False)
    bottleneck_df.to_parquet(bottle_path, index=False)
    forecast_df.to_parquet(forecast_path, index=False)

    total_time = time.time() - start_time
    print("\n" + "=" * 80)
    print(" DATASET GENERATION COMPLETE")
    print("=" * 80)
    print(f"Total Episodes Generated:      {len(episodes_df)}")
    print(f"Total Station Observations:    {len(telemetry_combined_df):,}")
    print(f"Total Vehicles Evaluated:      {len(vehicle_quality_df):,}")
    print(f"Total Vehicle Station Passes:  {len(vehicle_history_df):,}")
    print(f"Total Targets Computed:        {len(targets_combined_df):,}")
    print(f"Wall Clock Time:               {total_time:.2f}s ({total_time/num_episodes:.3f}s/episode)")
    print(f"Saved Datasets To:             {os.path.abspath(output_dir)}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Automotive Production Digital Twin Dataset Generator (Phase 2)")
    parser.add_argument("--episodes", "-e", type=int, default=100, help="Number of episodes to generate (default: 100)")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Master random seed (default: 42)")
    parser.add_argument("--output-dir", "-o", type=str, default="data", help="Output directory for parquet datasets (default: data)")
    parser.add_argument("--duration", "-d", type=float, default=80.0, help="Simulation duration in minutes (default: 80.0)")

    args = parser.parse_args()
    generate_dataset(
        num_episodes=args.episodes,
        master_seed=args.seed,
        output_dir=args.output_dir,
        duration_minutes=args.duration,
    )


if __name__ == "__main__":
    main()
