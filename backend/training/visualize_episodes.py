import os
import argparse
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def plot_episode_trajectories(data_dir: str = "data", output_image: str = "episode_trajectories.png"):
    episodes_path = os.path.join(data_dir, "episodes.parquet")
    telemetry_path = os.path.join(data_dir, "station_telemetry.parquet")

    if not os.path.exists(episodes_path) or not os.path.exists(telemetry_path):
        print(f"Error: Parquet files not found in {data_dir}.")
        return

    episodes_df = pd.read_parquet(episodes_path)
    telemetry_df = pd.read_parquet(telemetry_path)

    # Find a normal episode and an S3 degradation episode
    norm_ep_row = episodes_df[episodes_df["scenario_type"] == "NORMAL_OPERATION"]
    deg_ep_row = episodes_df[(episodes_df["scenario_type"] == "GRADUAL_STATION_DEGRADATION") & (episodes_df["affected_station"] == "S3")]

    if len(norm_ep_row) == 0 or len(deg_ep_row) == 0:
        # Fallback to any degradation episode
        deg_ep_row = episodes_df[episodes_df["scenario_type"] == "GRADUAL_STATION_DEGRADATION"]
        if len(deg_ep_row) == 0:
            deg_ep_row = episodes_df.iloc[[1]]
        if len(norm_ep_row) == 0:
            norm_ep_row = episodes_df.iloc[[0]]

    norm_id = norm_ep_row.iloc[0]["episode_id"]
    deg_id = deg_ep_row.iloc[0]["episode_id"]

    fig, axes = plt.subplots(7, 2, figsize=(16, 18), sharex=True)
    plt.subplots_adjust(hspace=0.35, wspace=0.2)

    for col_idx, (ep_id, title_prefix) in enumerate([(norm_id, "Healthy Normal Operation"), (deg_id, "S3 Gradual Degradation")]):
        ep_tel = telemetry_df[telemetry_df["episode_id"] == ep_id]
        s2 = ep_tel[ep_tel["station_id"] == "S2"].sort_values("timestamp")
        s3 = ep_tel[ep_tel["station_id"] == "S3"].sort_values("timestamp")
        s4 = ep_tel[ep_tel["station_id"] == "S4"].sort_values("timestamp")

        time_min = s3["timestamp"] / 60.0

        # 1. S3 Cycle Time
        axes[0, col_idx].plot(time_min, s3["cycle_time"], color="#f59e0b", lw=2, label="S3 Actual Cycle")
        axes[0, col_idx].plot(time_min, s3["baseline_cycle_time"], color="#94a3b8", ls="--", label="S3 Baseline")
        axes[0, col_idx].set_title(f"{title_prefix} ({ep_id})\nS3 Cycle Time (seconds)", fontsize=11, fontweight="bold")
        axes[0, col_idx].set_ylabel("Seconds")
        axes[0, col_idx].grid(True, alpha=0.3)
        axes[0, col_idx].legend(loc="upper left", fontsize=8)

        # 2. S3 Queue Length
        axes[1, col_idx].plot(time_min, s3["queue_length"], color="#ef4444", lw=2)
        axes[1, col_idx].set_title("S3 Upstream Queue Length", fontsize=10)
        axes[1, col_idx].set_ylabel("Vehicles")
        axes[1, col_idx].grid(True, alpha=0.3)

        # 3. B23 Buffer Occupancy
        axes[2, col_idx].plot(time_min, s2["buffer_occupancy"], color="#06b6d4", lw=2)
        axes[2, col_idx].axhline(5, color="#ef4444", ls=":", label="Capacity (5)")
        axes[2, col_idx].set_title("B23 Buffer Occupancy (S2 -> S3)", fontsize=10)
        axes[2, col_idx].set_ylabel("Vehicles")
        axes[2, col_idx].set_ylim(-0.2, 5.5)
        axes[2, col_idx].grid(True, alpha=0.3)

        # 4. S2 Blocking State
        axes[3, col_idx].fill_between(time_min, s2["is_blocked"], step="mid", color="#ec4899", alpha=0.5)
        axes[3, col_idx].set_title("S2 Upstream Blocking State (1 = Blocked)", fontsize=10)
        axes[3, col_idx].set_ylabel("State")
        axes[3, col_idx].set_ylim(-0.1, 1.1)
        axes[3, col_idx].grid(True, alpha=0.3)

        # 5. B34 Buffer Occupancy
        axes[4, col_idx].plot(time_min, s3["buffer_occupancy"], color="#8b5cf6", lw=2)
        axes[4, col_idx].set_title("B34 Buffer Occupancy (S3 -> S4)", fontsize=10)
        axes[4, col_idx].set_ylabel("Vehicles")
        axes[4, col_idx].set_ylim(-0.2, 5.5)
        axes[4, col_idx].grid(True, alpha=0.3)

        # 6. S4 Starvation State
        axes[5, col_idx].fill_between(time_min, s4["is_starved"], step="mid", color="#3b82f6", alpha=0.5)
        axes[5, col_idx].set_title("S4 Downstream Starvation State (1 = Starved)", fontsize=10)
        axes[5, col_idx].set_ylabel("State")
        axes[5, col_idx].set_ylim(-0.1, 1.1)
        axes[5, col_idx].grid(True, alpha=0.3)

        # 7. Station Utilization Comparison
        axes[6, col_idx].plot(time_min, s2["utilization"], label="S2", color="#06b6d4")
        axes[6, col_idx].plot(time_min, s3["utilization"], label="S3", color="#f59e0b")
        axes[6, col_idx].plot(time_min, s4["utilization"], label="S4", color="#8b5cf6")
        axes[6, col_idx].set_title("Station Utilization (%)", fontsize=10)
        axes[6, col_idx].set_ylabel("Util %")
        axes[6, col_idx].set_xlabel("Simulation Time (Minutes)", fontsize=10)
        axes[6, col_idx].set_ylim(0, 105)
        axes[6, col_idx].grid(True, alpha=0.3)
        axes[6, col_idx].legend(loc="lower left", fontsize=8)

    plt.savefig(output_image, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[Plot] Saved trajectory comparison figure to {os.path.abspath(output_image)}")


def main():
    parser = argparse.ArgumentParser(description="Episode Trajectory Visualizer")
    parser.add_argument("--data-dir", "-d", type=str, default="data", help="Directory containing parquet datasets")
    parser.add_argument("--output", "-o", type=str, default="episode_trajectories.png", help="Output PNG file path")
    args = parser.parse_args()
    plot_episode_trajectories(args.data_dir, args.output)


if __name__ == "__main__":
    main()
