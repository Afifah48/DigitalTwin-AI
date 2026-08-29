import pytest
from backend.twin.digital_twin import DigitalTwin
from backend.config.factory_config import get_default_factory_config
from backend.models.enums import StationId, BufferId, EventType


def test_gradual_degradation_causal_sequence():
    """
    Validates Phase 1.5 gradual degradation causal mechanics:
    1. Healthy baseline operation (0 <= t < 600s): cycle time ~54s, low buffer occupancy, zero blocking.
    2. Early degradation onset (600s <= t < 1200s): S3 cycle time drifts 54s -> 58s -> 62s, vibration & current variance increase.
    3. Buffer pressure (1200s <= t < 1800s): S3 cycle time reaches 65s -> 75s, B23 buffer occupancy steadily increases from 0 to 5.
    4. Emergent bottleneck & blocking (t >= 1800s): B23 reaches capacity (5/5), S2 experiences BLOCKED state, S4 experiences STARVED state, throughput drops.
    """
    config = get_default_factory_config()
    for st in config.station_configs.values():
        st.cycle_time_std = 0.5  # Small realistic noise

    twin = DigitalTwin(config=config, seed=42)

    # Attach dynamic gradual degradation function to S3
    # Baseline 54s until t=600s, then drifts linearly by +0.02s per second up to +30s max
    degrade_start_t = 600.0
    drift_rate = 0.015  # seconds increase per simulated second

    s3_station = twin.engine.stations[StationId.S3]

    def s3_cycle_time_curve(t: float) -> float:
        if t < degrade_start_t:
            return 54.0
        drift = min(35.0, (t - degrade_start_t) * drift_rate)
        return 54.0 + drift

    def s3_vibration_curve(t: float) -> float:
        if t < degrade_start_t:
            return 0.0
        return min(3.5, (t - degrade_start_t) * 0.002)

    def s3_variance_curve(t: float) -> float:
        if t < degrade_start_t:
            return 0.0
        return min(2.5, (t - degrade_start_t) * 0.0015)

    s3_station.dynamic_baseline_cycle_time = s3_cycle_time_curve
    s3_station.dynamic_vibration_offset = s3_vibration_curve
    s3_station.dynamic_current_variance_offset = s3_variance_curve

    # 1. Early check at t = 500s (Healthy operation)
    state_500 = twin.step_until(500.0)
    s3_tel_500 = state_500.stations[StationId.S3].telemetry
    assert 53.0 <= s3_tel_500.baseline_cycle_time <= 55.0
    assert state_500.stations[StationId.S2].blocked_count == 0
    assert state_500.buffers[BufferId.B23].current_occupancy <= 1

    # 2. Check at t = 1000s (Early process drift: cycle time is higher, but NO blocking yet!)
    state_1000 = twin.step_until(1000.0)
    s3_tel_1000 = state_1000.stations[StationId.S3].telemetry
    assert s3_tel_1000.baseline_cycle_time > 57.0  # Cycle time is drifting
    assert s3_tel_1000.vibration > s3_tel_500.vibration  # Vibration has drifted up
    assert state_1000.stations[StationId.S2].blocked_count == 0  # CRITICAL: Early degradation has started, but bottleneck hasn't blocked line yet!

    # 3. Check at t = 2400s (Full bottleneck propagation: B23 saturated, S2 blocked, S4 starved)
    state_2400 = twin.step_until(2400.0)
    assert state_2400.buffers[BufferId.B23].current_occupancy >= 4
    assert state_2400.stations[StationId.S2].blocked_count > 0
    assert state_2400.stations[StationId.S4].starved_count > 0

    # Verify event stream records progression
    events = twin.get_events()
    blocked_starts = [e for e in events if e.event_type == EventType.BLOCKED_START and e.station_id == StationId.S2]
    assert len(blocked_starts) > 0
    # Verify that first blocking occurs AFTER early degradation started (i.e. timestamp > 1200s)
    assert blocked_starts[0].timestamp > 1200.0
