import argparse
import sys
from backend.twin.digital_twin import DigitalTwin
from backend.config.factory_config import get_default_factory_config
from backend.models.enums import EventType, StationId, BufferId


def run_demo(duration_minutes: float = 60.0, export_csv: bool = False, export_json: bool = False):
    duration_seconds = duration_minutes * 60.0

    print("=" * 80)
    print(" AUTOMOTIVE PRODUCTION DIGITAL TWIN - DISCRETE-EVENT SIMULATOR (PHASE 1)")
    print("=" * 80)
    print(f"Simulating factory line for {duration_minutes:.1f} minutes ({duration_seconds:.0f} seconds)...")
    print(f"Target Takt Time: 54.0s | Finite Buffer Capacities: 5 vehicles")
    print("-" * 80)

    config = get_default_factory_config()
    twin = DigitalTwin(config=config, seed=42)
    state = twin.simulate(duration_seconds)
    events = twin.get_events()

    print("\n" + "=" * 80)
    print(" SIMULATION SUMMARY REPORT")
    print("=" * 80)
    print(f"Simulation Duration:     {state.simulation_time / 60.0:.1f} minutes ({state.simulation_time:.0f}s)")
    print(f"Total Throughput:        {state.total_throughput} finished vehicles")
    print(f"Actual Throughput Rate:  {state.throughput_uph:.1f} Units Per Hour (UPH)")
    print(f"Average Cycle Time:      {state.average_cycle_time:.1f} seconds (Target: {state.target_takt_time:.1f}s)")
    print(f"Overall Factory Util:    {state.system_utilization:.1f}%")
    print(f"Total Discrete Events:   {len(events)} logged")

    # Station Metrics Table
    print("\n" + "-" * 80)
    print(f"{'Station':<8} {'Name':<22} {'Baseline':<10} {'Avg Cycle':<10} {'Util %':<8} {'Processed':<10} {'Blocked':<8} {'Starved':<8}")
    print("-" * 80)

    for st_id in [StationId.S1, StationId.S2, StationId.S3, StationId.S4, StationId.S5, StationId.S6]:
        st = state.stations[st_id]
        tel = st.telemetry
        print(
            f"{st_id.value:<8} "
            f"{st.name:<22} "
            f"{tel.baseline_cycle_time:<10.1f} "
            f"{tel.cycle_time:<10.1f} "
            f"{tel.utilization:<8.1f} "
            f"{st.total_processed:<10} "
            f"{st.blocked_count:<8} "
            f"{st.starved_count:<8}"
        )
    print("-" * 80)

    # Finite Buffer Metrics Table
    print("\n" + "-" * 80)
    print(f"{'Buffer':<8} {'Between':<16} {'Capacity':<10} {'Current Occ':<12} {'Max Queue (Peak)':<18} {'Total Entries':<14}")
    print("-" * 80)

    for buf_id in [BufferId.B12, BufferId.B23, BufferId.B34, BufferId.B45, BufferId.B56]:
        buf = state.buffers[buf_id]
        between = f"{buf.upstream_station_id.value} -> {buf.downstream_station_id.value}"
        print(
            f"{buf_id.value:<8} "
            f"{between:<16} "
            f"{buf.capacity:<10} "
            f"{buf.current_occupancy:<12} "
            f"{buf.peak_occupancy:<18} "
            f"{buf.total_entries:<14}"
        )
    print("-" * 80)

    # Event Breakdown
    blocked_events = [e for e in events if e.event_type == EventType.BLOCKED_START]
    starved_events = [e for e in events if e.event_type == EventType.STARVED_START]
    completed_events = [e for e in events if e.event_type == EventType.PROCESSING_COMPLETE]

    print("\n" + "-" * 80)
    print(" EVENT BREAKDOWN")
    print("-" * 80)
    print(f"Total Processing Cycles Completed: {len(completed_events)}")
    print(f"Total Blocked Events Triggered:     {len(blocked_events)}")
    print(f"Total Starved Events Triggered:     {len(starved_events)}")
    print("=" * 80)

    if export_csv:
        csv_file = "factory_events.csv"
        twin.export_event_log_csv(csv_file)
        print(f"[Export] Saved event stream to {csv_file}")

    if export_json:
        json_file = "factory_events.json"
        twin.export_event_log_json(json_file)
        print(f"[Export] Saved event stream to {json_file}")


def main():
    parser = argparse.ArgumentParser(description="Automotive Production Digital Twin Core Simulator (Phase 1)")
    parser.add_argument(
        "--duration",
        "-d",
        type=float,
        default=60.0,
        help="Simulation duration in minutes (default: 60.0)",
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Export event logs to CSV file",
    )
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export event logs to JSON file",
    )

    args = parser.parse_args()
    run_demo(duration_minutes=args.duration, export_csv=args.export_csv, export_json=args.export_json)


if __name__ == "__main__":
    main()
