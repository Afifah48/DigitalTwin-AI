import pytest
from backend.config.factory_config import get_default_factory_config
from backend.models.enums import StationId, BufferId
from backend.counterfactual.models import InterventionType, CounterfactualAction
from backend.counterfactual.simulator import CounterfactualSimulator


def test_counterfactual_baseline_equivalence():
    """If intervention magnitude is 0, baseline and counterfactual should match."""
    config = get_default_factory_config()
    simulator = CounterfactualSimulator(base_config=config, simulation_duration=1000, seed=42)

    action = CounterfactualAction(
        target_station=StationId.S2,
        action_type=InterventionType.CYCLE_TIME_REDUCTION,
        magnitude=0.0,
    )

    result = simulator.simulate(action)

    assert result.throughput_delta == 0.0
    assert result.risk_delta == 0.0
    assert result.baseline_throughput == result.counterfactual_throughput
    assert result.baseline_bottleneck_station == result.counterfactual_bottleneck_station


def test_counterfactual_cycle_time_improvement():
    """Reducing cycle time at the slowest station should improve or maintain throughput."""
    config = get_default_factory_config()
    # Make S1 extremely slow so it dominates even in short simulations
    config.station_configs[StationId.S1].baseline_cycle_time = 100.0

    simulator = CounterfactualSimulator(base_config=config, simulation_duration=3600, seed=42)

    # Intervention: Reduce S1 cycle time by 46s (bringing it to 54s, matching others)
    action = CounterfactualAction(
        target_station=StationId.S1,
        action_type=InterventionType.CYCLE_TIME_REDUCTION,
        magnitude=-46.0,
    )

    result = simulator.simulate(action)

    # Throughput should increase because the bottleneck was relieved
    assert result.throughput_delta >= 0.0
    # Counterfactual risk should be <= baseline risk
    assert result.counterfactual_risk <= result.baseline_risk


def test_counterfactual_buffer_expansion():
    """Expanding a buffer should alter the counterfactual config correctly."""
    config = get_default_factory_config()
    config.station_configs[StationId.S3].baseline_cycle_time = 70.0

    simulator = CounterfactualSimulator(base_config=config, simulation_duration=1000, seed=42)

    action = CounterfactualAction(
        target_buffer=BufferId.B23,
        action_type=InterventionType.BUFFER_EXPANSION,
        magnitude=10.0,
    )

    result = simulator.simulate(action)

    # Verify the config was mutated correctly
    cf_config = simulator.apply_action_to_config(simulator.base_config, action)
    assert cf_config.buffer_configs[BufferId.B23].capacity == 15

    # Result should be a valid CounterfactualResult
    assert result.baseline_throughput >= 0.0
    assert result.counterfactual_throughput >= 0.0


def test_invalid_intervention_rejected():
    """Missing target for buffer expansion should raise ValueError."""
    with pytest.raises(ValueError, match="requires a target_buffer"):
        action = CounterfactualAction(
            target_station=StationId.S1,
            action_type=InterventionType.BUFFER_EXPANSION,
            magnitude=5.0,
        )
        action.validate_target()


def test_deterministic_simulation():
    """Same config + seed should produce identical results."""
    config = get_default_factory_config()
    config.station_configs[StationId.S4].baseline_cycle_time = 75.0

    action = CounterfactualAction(
        target_station=StationId.S4,
        action_type=InterventionType.CYCLE_TIME_REDUCTION,
        magnitude=-10.0,
    )

    sim1 = CounterfactualSimulator(base_config=config, simulation_duration=600, seed=42)
    r1 = sim1.simulate(action)

    sim2 = CounterfactualSimulator(base_config=config, simulation_duration=600, seed=42)
    r2 = sim2.simulate(action)

    assert r1.baseline_throughput == r2.baseline_throughput
    assert r1.counterfactual_throughput == r2.counterfactual_throughput
    assert r1.risk_delta == r2.risk_delta


@pytest.mark.parametrize("station_id", [
    StationId.S1, StationId.S2, StationId.S3,
    StationId.S4, StationId.S5, StationId.S6,
])
def test_counterfactual_works_all_stations(station_id):
    """Counterfactual simulation works generically for S1-S6."""
    config = get_default_factory_config()
    simulator = CounterfactualSimulator(base_config=config, simulation_duration=600, seed=42)

    action = CounterfactualAction(
        target_station=station_id,
        action_type=InterventionType.CYCLE_TIME_REDUCTION,
        magnitude=-2.0,
    )

    result = simulator.simulate(action)
    assert result.baseline_analysis is not None
    assert result.counterfactual_analysis is not None
    assert len(result.baseline_analysis.station_ranking) == 6


def test_downtime_reduction_intervention():
    """Downtime reduction should apply cleanly to config."""
    config = get_default_factory_config()
    config.station_configs[StationId.S2].failure_probability = 0.05

    simulator = CounterfactualSimulator(base_config=config, simulation_duration=600, seed=42)

    action = CounterfactualAction(
        target_station=StationId.S2,
        action_type=InterventionType.DOWNTIME_REDUCTION,
        magnitude=-0.03,
    )

    cf_config = simulator.apply_action_to_config(config, action)
    assert cf_config.station_configs[StationId.S2].failure_probability == pytest.approx(0.02)

    result = simulator.simulate(action)
    assert result.baseline_analysis is not None
