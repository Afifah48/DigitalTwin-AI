import pytest
from backend.twin.digital_twin import DigitalTwin
from backend.config.factory_config import get_default_factory_config
from backend.models.enums import StationId, MachineState


def test_normal_production_flow():
    """Verify that vehicles flow sequentially through all 6 stations in steady-state production."""
    config = get_default_factory_config()
    # Set standard deviation to 0 for exact deterministic test
    for st_cfg in config.station_configs.values():
        st_cfg.cycle_time_std = 0.0
    config.input_arrival_std = 0.0

    twin = DigitalTwin(config=config, seed=42)
    # Simulate for 1800 seconds (30 minutes)
    state = twin.simulate(1800.0)

    assert state.simulation_time == 1800.0
    assert state.total_throughput > 0
    assert len(state.completed_vehicles) == state.total_throughput

    # Check vehicle progression through all 6 stations
    first_vehicle = state.completed_vehicles[0]
    stations_visited = [p.station_id for p in first_vehicle.history]
    expected_order = [
        StationId.S1,
        StationId.S2,
        StationId.S3,
        StationId.S4,
        StationId.S5,
        StationId.S6,
    ]
    assert stations_visited == expected_order

    # Verify timestamps are strictly increasing in vehicle history
    for i in range(len(first_vehicle.history) - 1):
        curr_pass = first_vehicle.history[i]
        next_pass = first_vehicle.history[i + 1]
        assert curr_pass.completed_at <= next_pass.entered_at


def test_station_utilization_and_states():
    """Verify that stations achieve healthy operational utilization during normal steady state."""
    config = get_default_factory_config()
    twin = DigitalTwin(config=config, seed=123)
    state = twin.simulate(3600.0)  # 1 hour

    assert state.total_throughput >= 40  # With 54s takt time, nominal ~60-66 units minus warm-up
    assert state.system_utilization > 50.0

    for st_id, st_state in state.stations.items():
        assert st_state.total_processed > 0
        assert st_state.telemetry.utilization > 0.0
