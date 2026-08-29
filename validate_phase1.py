"""
Validation script for Phase 1 of Automotive Production Digital Twin backend.
Executes detailed technical validations for Steps 2 to 13.
"""

import sys
import numpy as np
from backend.twin.digital_twin import DigitalTwin
from backend.config.factory_config import get_default_factory_config
from backend.models.enums import StationId, BufferId, MachineState, EventType


def validate_step2_topology():
    print("\n" + "="*80)
    print("STEP 2: FACTORY TOPOLOGY VALIDATION")
    print("="*80)
    config = get_default_factory_config()
    twin = DigitalTwin(config=config, seed=42)
    state = twin.get_state()

    stations = list(state.stations.keys())
    buffers = list(state.buffers.keys())

    print(f"Stations count: {len(stations)} -> {[s.value for s in stations]}")
    print(f"Buffers count:  {len(buffers)} -> {[b.value for b in buffers]}")
    print(f"Target Takt Time: {state.target_takt_time}s")
    for b_id, b_state in state.buffers.items():
        print(f"  Buffer {b_id.value}: {b_state.upstream_station_id.value} -> {b_state.downstream_station_id.value} (Capacity: {b_state.capacity})")

    assert len(stations) == 6, f"Expected 6 stations, found {len(stations)}"
    assert len(buffers) == 5, f"Expected 5 buffers, found {len(buffers)}"
    for b_id, b_state in state.buffers.items():
        assert b_state.capacity == 5, f"Buffer {b_id} capacity is {b_state.capacity}, expected 5"
    assert state.target_takt_time == 54.0, f"Target takt time is {state.target_takt_time}, expected 54.0"
    print(">>> Topology validation PASSED.")


def validate_step3_normal_production():
    print("\n" + "="*80)
    print("STEP 3: NORMAL PRODUCTION VALIDATION (60 MIN / 3600s)")
    print("="*80)
    config = get_default_factory_config()
    # Fully deterministic run with seed
    twin = DigitalTwin(config=config, seed=42)
    state = twin.simulate(3600.0)
    events = twin.get_events()

    print(f"Completed Vehicles:      {state.total_throughput}")
    print(f"Throughput UPH:          {state.throughput_uph} units/hour")
    print(f"Average Cycle Time:      {state.average_cycle_time:.2f}s")
    print(f"System Utilization:      {state.system_utilization:.1f}%")
    print(f"Total Discrete Events:   {len(events)}")

    print("\nPer-Station Details:")
    for st_id in [StationId.S1, StationId.S2, StationId.S3, StationId.S4, StationId.S5, StationId.S6]:
        st = state.stations[st_id]
        print(f"  Station {st_id.value:<2} ({st.name:<18}): Busy={st.total_busy_time:.1f}s, Util={st.telemetry.utilization:.1f}%, Blocked={st.total_blocked_time:.1f}s (cnt={st.blocked_count}), Starved={st.total_starved_time:.1f}s (cnt={st.starved_count}), Processed={st.total_processed}")

    print("\nPer-Buffer Max Occupancy:")
    for b_id, b_state in state.buffers.items():
        print(f"  Buffer {b_id.value}: Peak Occupancy={b_state.peak_occupancy}/{b_state.capacity}, Current={b_state.current_occupancy}")

    print(">>> Normal production validation complete.")


def validate_step4_finite_buffers():
    print("\n" + "="*80)
    print("STEP 4: FINITE BUFFER BOUNDS VALIDATION (0 <= OCC <= CAPACITY)")
    print("="*80)
    config = get_default_factory_config()
    twin = DigitalTwin(config=config, seed=42)
    state = twin.simulate(3600.0)
    events = twin.get_events()

    violations = []
    # Check all events that record buffer occupancy
    for e in events:
        if e.buffer_id:
            cap = config.buffer_configs[e.buffer_id].capacity
            if e.buffer_before is not None and not (0 <= e.buffer_before <= cap):
                violations.append(f"Event at {e.timestamp:.1f}s: buffer_before={e.buffer_before} outside [0, {cap}] for {e.buffer_id}")
            if e.buffer_after is not None and not (0 <= e.buffer_after <= cap):
                violations.append(f"Event at {e.timestamp:.1f}s: buffer_after={e.buffer_after} outside [0, {cap}] for {e.buffer_id}")

    print(f"Checked {len(events)} events across all 5 buffers.")
    if violations:
        print(f"FAILED: {len(violations)} buffer capacity violations detected:")
        for v in violations[:10]:
            print(" ", v)
    else:
        print(">>> SUCCESS: 0 buffer bound violations. All buffers strictly obeyed 0 <= occupancy <= 5.")


def validate_step5_and_6_s3_degradation():
    print("\n" + "="*80)
    print("STEP 5 & 6: S3 DEGRADATION CAUSAL TRACE (BLOCKING & STARVATION)")
    print("="*80)
    config = get_default_factory_config()
    for st in config.station_configs.values():
        st.cycle_time_std = 0.0
    config.input_arrival_std = 0.0

    # Bottleneck S3 by setting baseline to 300.0s (slower than 54s takt)
    config.station_configs[StationId.S3].baseline_cycle_time = 300.0

    twin = DigitalTwin(config=config, seed=42)
    state = twin.simulate(1200.0)
    events = twin.get_events()

    print("Tracing S3 Degradation Events (first 10 relevant events):")
    relevant = [e for e in events if e.station_id in (StationId.S2, StationId.S3, StationId.S4) or e.buffer_id in (BufferId.B23, BufferId.B34)]
    
    # Print chronological causal chain
    b23_entries = [e for e in events if e.event_type == EventType.BUFFER_ENTER and e.buffer_id == BufferId.B23]
    b23_full = [e for e in events if e.buffer_id == BufferId.B23 and e.buffer_after == 5]
    s2_blocked = [e for e in events if e.event_type == EventType.BLOCKED_START and e.station_id == StationId.S2]
    s4_starved = [e for e in events if e.event_type == EventType.STARVED_START and e.station_id == StationId.S4]

    print("\nCausal Evidence for S2 Blocking:")
    for ev in b23_entries[:6]:
        print(f"  t={ev.timestamp:6.1f}s | B23 BUFFER_ENTER by {ev.vehicle_id} -> B23 occupancy={ev.buffer_after}/5")
    if s2_blocked:
        print(f"  t={s2_blocked[0].timestamp:6.1f}s | S2 BLOCKED_START (S2 cannot release vehicle into full B23)")
    
    print("\nCausal Evidence for S4 Starvation:")
    for ev in s4_starved[:3]:
        print(f"  t={ev.timestamp:6.1f}s | S4 STARVED_START (B34 is empty because S3 is still processing)")

    print(f"\nFinal State Checks:")
    print(f"  B23 Occupancy: {state.buffers[BufferId.B23].current_occupancy}/5")
    print(f"  S2 Blocked count: {state.stations[StationId.S2].blocked_count}, Total Blocked Time: {state.stations[StationId.S2].total_blocked_time:.1f}s")
    print(f"  B34 Occupancy: {state.buffers[BufferId.B34].current_occupancy}/5")
    print(f"  S4 Starved count: {state.stations[StationId.S4].starved_count}, Total Starved Time: {state.stations[StationId.S4].total_starved_time:.1f}s")


def validate_step7_arbitrary_station_degradation():
    print("\n" + "="*80)
    print("STEP 7: ARBITRARY STATION (S4) DEGRADATION TEST")
    print("="*80)
    config = get_default_factory_config()
    for st in config.station_configs.values():
        st.cycle_time_std = 0.0

    # Bottleneck S4 (baseline = 350.0s)
    config.station_configs[StationId.S4].baseline_cycle_time = 350.0

    twin = DigitalTwin(config=config, seed=99)
    state = twin.simulate(1200.0)

    print(f"Testing S4 Bottleneck (350s baseline):")
    print(f"  B34 (Upstream Buffer to S4) Occupancy: {state.buffers[BufferId.B34].current_occupancy}/5")
    print(f"  S3 (Upstream Station) Blocked Count:   {state.stations[StationId.S3].blocked_count}, Blocked Time: {state.stations[StationId.S3].total_blocked_time:.1f}s")
    print(f"  B45 (Downstream Buffer from S4) Occ:   {state.buffers[BufferId.B45].current_occupancy}/5")
    print(f"  S5 (Downstream Station) Starved Count: {state.stations[StationId.S5].starved_count}, Starved Time: {state.stations[StationId.S5].total_starved_time:.1f}s")

    assert state.stations[StationId.S3].blocked_count > 0, "S3 should be blocked by full B34"
    assert state.stations[StationId.S5].starved_count > 0, "S5 should be starved by empty B45"
    print(">>> S4 Degradation correctly propagated blocking to S3 and starvation to S5 via generic mechanics.")


def validate_step8_downtime():
    print("\n" + "="*80)
    print("STEP 8: DETERMINISTIC MACHINE DOWNTIME & RECOVERY")
    print("="*80)
    config = get_default_factory_config()
    for st in config.station_configs.values():
        st.cycle_time_std = 0.0

    # Station S2 experiences deterministic breakdown: 100% failure on 1st cycle, repair time 150s
    config.station_configs[StationId.S2].failure_probability = 1.0
    config.station_configs[StationId.S2].repair_time = 150.0
    config.station_configs[StationId.S2].repair_time_std = 0.0

    twin = DigitalTwin(config=config, seed=7)
    state = twin.simulate(600.0)
    events = twin.get_events()

    down_starts = [e for e in events if e.event_type == EventType.DOWN_START and e.station_id == StationId.S2]
    down_ends = [e for e in events if e.event_type == EventType.DOWN_END and e.station_id == StationId.S2]

    print(f"S2 Down starts logged: {len(down_starts)}")
    for ds, de in zip(down_starts, down_ends):
        print(f"  Breakdown at t={ds.timestamp:.1f}s -> Repair completed at t={de.timestamp:.1f}s (Duration: {de.timestamp - ds.timestamp:.1f}s)")

    s2 = state.stations[StationId.S2]
    print(f"S2 Total Down Time: {s2.total_down_time:.1f}s, Total Processed: {s2.total_processed}")
    assert len(down_starts) > 0
    assert len(down_ends) > 0
    assert s2.total_processed > 0, "S2 must resume processing after repair"
    print(">>> Downtime and recovery verified.")


def validate_step9_vehicle_flow():
    print("\n" + "="*80)
    print("STEP 9: VEHICLE PROGRESSION STATE TRACE")
    print("="*80)
    config = get_default_factory_config()
    twin = DigitalTwin(config=config, seed=42)
    state = twin.simulate(1800.0)

    sample_vehicles = state.completed_vehicles[:3]
    for v in sample_vehicles:
        print(f"\nVehicle ID: {v.id} | Model: {v.model.value} | VIN: {v.vin} | Total Transit: {v.total_transit_time:.1f}s")
        print(f"  Station Passes ({len(v.history)} total):")
        for p in v.history:
            print(f"    Station {p.station_id.value:<2}: Entered={p.entered_at:6.1f}s, Completed={p.completed_at:6.1f}s, Actual Cycle={p.actual_cycle_time:4.1f}s, Deviation={p.deviation_at_pass:+.2f}")

    for v in sample_vehicles:
        st_ids = [p.station_id for p in v.history]
        assert st_ids == [StationId.S1, StationId.S2, StationId.S3, StationId.S4, StationId.S5, StationId.S6]
    print(">>> Vehicle progression state flow verified.")


def validate_step10_event_logging():
    print("\n" + "="*80)
    print("STEP 10: EVENT LOGGING SCHEMA & DATA INTEGRITY CHECK")
    print("="*80)
    config = get_default_factory_config()
    twin = DigitalTwin(config=config, seed=42)
    state = twin.simulate(1800.0)
    events = twin.get_events()

    proc_events = [e for e in events if e.event_type == EventType.PROCESSING_COMPLETE]
    print(f"Auditing {len(proc_events)} PROCESSING_COMPLETE events...")

    missing_fields = 0
    impossible_values = 0

    for idx, e in enumerate(proc_events):
        if e.timestamp is None or e.vehicle_id is None or e.station_id is None or e.cycle_time is None:
            missing_fields += 1
        if e.queue_before is None or e.queue_after is None or e.buffer_before is None or e.buffer_after is None:
            missing_fields += 1
        if e.cycle_time <= 0 or e.queue_before < 0 or e.queue_after < 0 or e.buffer_before < 0 or e.buffer_after < 0:
            impossible_values += 1

    print(f"Missing Fields Count:      {missing_fields}")
    print(f"Impossible Values Count:   {impossible_values}")
    assert missing_fields == 0
    assert impossible_values == 0
    print(">>> Event logging schema check PASSED.")


def validate_step11_throughput_sanity():
    print("\n" + "="*80)
    print("STEP 11: THEORETICAL VS OBSERVED THROUGHPUT SANITY")
    print("="*80)
    config = get_default_factory_config()
    for st in config.station_configs.values():
        st.cycle_time_std = 0.0
    config.input_arrival_std = 0.0

    twin = DigitalTwin(config=config, seed=42)
    state = twin.simulate(3600.0)

    # In 6-station line:
    # S1: 52s, S2: 54s, S3: 54s, S4: 51s, S5: 53s, S6: 55s
    # Bottleneck cycle time = max(cycle_times) = 55.0s (S6)
    # Target takt time = 54.0s
    # Inflow arrival interval = 54.0s
    # Warmup time for first vehicle = 52 + 54 + 54 + 51 + 53 + 55 = 319.0s
    # Steady state available time = 3600 - 319 = 3281s
    # Since S6 is 55.0s, steady state output after 1st vehicle = 3281 / 55 = ~59.65 vehicles
    # Total theoretical completed in 3600s = 1 + 59 = 60 vehicles.
    
    print(f"Line Bottleneck Station: S6 (Baseline = 55.0s)")
    print(f"Warm-up Transit Duration: 319.0s")
    print(f"Theoretical Steady-State Max Vehicles in 3600s: 60 vehicles")
    print(f"Actual Observed Completed Vehicles:             {state.total_throughput} vehicles")
    print(f"Actual Observed UPH:                            {state.throughput_uph} UPH")
    
    assert state.total_throughput == 60, f"Expected 60 completed vehicles, got {state.total_throughput}"
    print(">>> Throughput sanity check PASSED. Matches mathematical discrete-event theoretical capacity precisely.")


def validate_step13_determinism_and_randomness():
    print("\n" + "="*80)
    print("STEP 13: REPRODUCIBILITY & STOCHASTICITY TEST")
    print("="*80)
    config1 = get_default_factory_config()
    twin1 = DigitalTwin(config=config1, seed=12345)
    state1 = twin1.simulate(1800.0)

    config2 = get_default_factory_config()
    twin2 = DigitalTwin(config=config2, seed=12345)
    state2 = twin2.simulate(1800.0)

    config3 = get_default_factory_config()
    twin3 = DigitalTwin(config=config3, seed=99999)
    state3 = twin3.simulate(1800.0)

    print(f"Seed 12345 (Run 1): Throughput={state1.total_throughput}, AvgCycle={state1.average_cycle_time:.3f}, SystemUtil={state1.system_utilization:.2f}%")
    print(f"Seed 12345 (Run 2): Throughput={state2.total_throughput}, AvgCycle={state2.average_cycle_time:.3f}, SystemUtil={state2.system_utilization:.2f}%")
    print(f"Seed 99999 (Run 3): Throughput={state3.total_throughput}, AvgCycle={state3.average_cycle_time:.3f}, SystemUtil={state3.system_utilization:.2f}%")

    assert state1.total_throughput == state2.total_throughput
    assert state1.average_cycle_time == state2.average_cycle_time
    assert state1.system_utilization == state2.system_utilization

    assert state1.average_cycle_time != state3.average_cycle_time or state1.system_utilization != state3.system_utilization
    print(">>> Determinism on identical seed and variability on distinct seed verified.")


if __name__ == "__main__":
    validate_step2_topology()
    validate_step3_normal_production()
    validate_step4_finite_buffers()
    validate_step5_and_6_s3_degradation()
    validate_step7_arbitrary_station_degradation()
    validate_step8_downtime()
    validate_step9_vehicle_flow()
    validate_step10_event_logging()
    validate_step11_throughput_sanity()
    validate_step13_determinism_and_randomness()
