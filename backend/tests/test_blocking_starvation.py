import pytest
from backend.twin.digital_twin import DigitalTwin
from backend.config.factory_config import get_default_factory_config
from backend.models.enums import StationId, BufferId, MachineState, EventType


def test_s3_bottleneck_causes_s2_blocking_and_s4_starvation():
    """
    Test that when S3 slows down significantly:
    1. Buffer B23 reaches full capacity (5).
    2. Station S2 transitions to BLOCKED.
    3. Buffer B34 empties (0).
    4. Station S4 transitions to STARVED.
    """
    config = get_default_factory_config()
    for st in config.station_configs.values():
        st.cycle_time_std = 0.0

    # Intentionally bottleneck S3 with huge cycle time (e.g. 500s)
    config.station_configs[StationId.S3].baseline_cycle_time = 500.0

    twin = DigitalTwin(config=config, seed=42)
    state = twin.simulate(1800.0)

    # Check buffer B23 saturation
    assert state.buffers[BufferId.B23].current_occupancy == config.buffer_configs[BufferId.B23].capacity
    assert state.buffers[BufferId.B23].peak_occupancy == 5

    # Check that S2 experienced blocking
    assert state.stations[StationId.S2].blocked_count > 0
    assert state.stations[StationId.S2].total_blocked_time > 0

    # Check buffer B34 starvation
    assert state.buffers[BufferId.B34].current_occupancy == 0

    # Check that S4 experienced starvation
    assert state.stations[StationId.S4].starved_count > 0
    assert state.stations[StationId.S4].total_starved_time > 0

    # Verify event stream records blocked and starved events
    events = twin.get_events()
    blocked_events = [e for e in events if e.event_type == EventType.BLOCKED_START and e.station_id == StationId.S2]
    starved_events = [e for e in events if e.event_type == EventType.STARVED_START and e.station_id == StationId.S4]

    assert len(blocked_events) > 0
    assert len(starved_events) > 0


def test_arbitrary_station_blocking_not_hardcoded():
    """
    Verify flow-based emergence: Slowing down S5 must block S4 and starve S6.
    Proves that blocking & starvation logic is general and not hardcoded to S3.
    """
    config = get_default_factory_config()
    for st in config.station_configs.values():
        st.cycle_time_std = 0.0

    # Slow down S5 to 400s
    config.station_configs[StationId.S5].baseline_cycle_time = 400.0

    twin = DigitalTwin(config=config, seed=99)
    state = twin.simulate(1800.0)

    # Buffer B45 fills up, blocking S4
    assert state.buffers[BufferId.B45].current_occupancy == 5
    assert state.stations[StationId.S4].blocked_count > 0
    assert state.stations[StationId.S4].total_blocked_time > 0

    # S6 starves because B56 is empty
    assert state.buffers[BufferId.B56].current_occupancy == 0
    assert state.stations[StationId.S6].starved_count > 0
    assert state.stations[StationId.S6].total_starved_time > 0
