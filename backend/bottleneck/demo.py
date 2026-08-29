"""
Phase 5 Real-Data Inference Demo
Runs the bottleneck pipeline against a real episode from data/station_telemetry.parquet
and prints a sample prediction with full evidence and ranking.
"""

import pandas as pd
from backend.models.enums import StationId
from backend.bottleneck.pipeline import BottleneckPipeline


def run_real_data_inference(data_dir: str = "data", episode_id: str = "EP_0001", target_timestamp: float = 2400.0):
    print("=" * 80)
    print(" PHASE 5 - REAL DATA INFERENCE DEMONSTRATION")
    print("=" * 80)

    tel_df = pd.read_parquet(f"{data_dir}/station_telemetry.parquet")
    episodes_df = pd.read_parquet(f"{data_dir}/episodes.parquet")
    targets_df = pd.read_parquet(f"{data_dir}/bottleneck_targets.parquet")

    ep_meta = episodes_df[episodes_df["episode_id"] == episode_id].iloc[0]
    print(f"\nEpisode: {episode_id}")
    print(f"  Scenario:  {ep_meta['scenario_type']}")
    print(f"  Severity:  {ep_meta['severity']}")
    print(f"  Station:   {ep_meta['affected_station']}")
    print(f"  Split:     {ep_meta['split']}")

    ep_df = tel_df[tel_df["episode_id"] == episode_id]
    timestamps = sorted(ep_df["timestamp"].unique())

    pipeline = BottleneckPipeline()

    # Run chronologically up to the target timestamp (no future leakage)
    result = None
    for t in timestamps:
        if t > target_timestamp:
            break
        t_df = ep_df[ep_df["timestamp"] == t]
        station_tels = {}
        for _, row in t_df.iterrows():
            st_id = StationId(row["station_id"])
            station_tels[st_id] = row.to_dict()
        result = pipeline.analyze_snapshot(t, station_tels)

    if result is None:
        print("No data available.")
        return

    print(f"\n{'-' * 80}")
    print(f" SNAPSHOT AT t = {target_timestamp:.0f}s ({target_timestamp/60:.1f} min)")
    print(f"{'-' * 80}")

    if result.predicted_bottleneck_station:
        print(f"\n  PRIMARY PREDICTED BOTTLENECK: {result.predicted_bottleneck_station.value}")
        print(f"  Risk Score:          {result.predicted_bottleneck_risk:.4f}")
        print(f"  Bottleneck Dominance:{result.bottleneck_dominance:.4f}")
        print(f"  Confidence:          {result.confidence:.4f}")
        if result.estimated_time_to_bottleneck_seconds is not None:
            print(f"  Estimated Time-to-Bottleneck: {result.estimated_time_to_bottleneck_seconds:.0f}s ({result.estimated_time_to_bottleneck_seconds/60:.1f} min)")
        if result.active_bottlenecks:
            print(f"  Active Bottlenecks:  {[s.value for s in result.active_bottlenecks]}")
        if result.constraint_migration:
            print(f"  Constraint Migration:{result.constraint_migration}")
    else:
        print("\n  PRIMARY PREDICTED BOTTLENECK: NONE (factory is nominal)")

    print(f"\n  INDUSTRIAL DIAGNOSIS:")
    print(f"  {result.summary}")

    print(f"\n{'-' * 80}")
    print(f" FULL STATION RANKING (S1-S6)")
    print(f"{'-' * 80}")
    print(f"  {'Station':<8} {'Risk':>8} {'Class':<14} {'Persist':>8} {'Conf':>8} {'TTB (s)':>10} {'Reason Codes'}")
    print(f"  {'-'*7} {'-'*8} {'-'*14} {'-'*8} {'-'*8} {'-'*10} {'-'*25}")
    for r in result.station_ranking:
        ttb_display = f"{r.time_to_bottleneck_seconds:.0f}s" if r.time_to_bottleneck_seconds is not None else "N/A"
        reasons_display = ", ".join(r.reason_codes[:2]) if r.reason_codes else "NOMINAL"
        print(
            f"  {r.station_id.value:<8} {r.risk_score:>8.4f} {r.prediction.value:<14} "
            f"{r.persistence_score:>8.4f} {r.confidence:>8.4f} {ttb_display:>10} {reasons_display}"
        )

    if result.predicted_bottleneck_station:
        primary = result.station_ranking[0]
        print(f"\n{'-' * 80}")
        print(f" EVIDENCE BREAKDOWN FOR {primary.station_id.value}")
        print(f"{'-' * 80}")
        if primary.evidence:
            for ev in primary.evidence[:5]:
                bar = "#" * int(ev.normalized_strength * 20)
                print(f"  {ev.signal:<35} [{bar:<20}] {ev.normalized_strength:.3f} ({ev.direction}) [{ev.source}]")
        else:
            print("  (No evidence signals recorded for nominal station)")

        print(f"\n  Reason Codes:               {primary.reason_codes}")
        print(f"  Upstream Blocking Risk:     {primary.upstream_blocking_risk:.4f}")
        print(f"  Downstream Starvation Risk: {primary.downstream_starvation_risk:.4f}")
        print(f"  Propagation Score:          {primary.propagation_score:.4f}")
        if primary.affected_stations:
            print(f"  Affected Neighbors:         {[s.value for s in primary.affected_stations]}")

    # Ground truth comparison
    print(f"\n{'-' * 80}")
    print(f" GROUND TRUTH COMPARISON (bottleneck_targets.parquet)")
    print(f"{'-' * 80}")
    t_targets = targets_df[
        (targets_df["episode_id"] == episode_id) &
        (targets_df["timestamp"] == target_timestamp)
    ]
    if len(t_targets) > 0:
        for _, row in t_targets.iterrows():
            gt = "YES (bottleneck will develop)" if row["bottleneck_in_horizon"] else "NO"
            print(f"  {row['station_id']:<8}: bottleneck_in_horizon = {gt}")
    else:
        print("  No ground truth available for this timestamp.")

    print("=" * 80)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 5 Real-Data Inference Demo")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--episode", default="EP_0001")
    parser.add_argument("--timestamp", type=float, default=2400.0)
    args = parser.parse_args()
    run_real_data_inference(args.data_dir, args.episode, args.timestamp)

