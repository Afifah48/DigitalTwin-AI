import pytest
from backend.twin.digital_twin import DigitalTwin
from backend.config.factory_config import get_default_factory_config
from backend.models.enums import StationId, EventType


def test_machine_breakdown_and_recovery():
    """Verify machine breakdown, repair duration timeout, and subsequent recovery to production."""
    config = get_default_factory_config()

    # Configure station S3 with deterministic failure: 100% failure probability on cycle
    config.station_configs[StationId.S3].failure_probability = 1.0
    config.station_configs[StationId.S3].repair_time = 60.0
    config.station_configs[StationId.S3].repair_time_std = 0.0
    for st in config.station_configs.values():
        st.cycle_time_std = 0.0

    twin = DigitalTwin(config=config, seed=1)
    state = twin.simulate(1000.0)

    s3_state = state.stations[StationId.S3]
    assert s3_state.down_count > 0
    assert s3_state.total_down_time >= 60.0

    # Verify that despite downtime, S3 recovers and completes vehicles
    assert s3_state.total_processed > 0

    # Verify breakdown and repair completed events
    events = twin.get_events()
    down_starts = [e for e in events if e.event_type == EventType.DOWN_START and e.station_id == StationId.S3]
    down_ends = [e for e in events if e.event_type == EventType.DOWN_END and e.station_id == StationId.S3]

    assert len(down_starts) > 0
    assert len(down_ends) > 0
    assert len(down_ends) >= len(down_starts) - 1
