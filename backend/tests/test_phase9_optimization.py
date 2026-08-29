import pytest
from backend.config.factory_config import get_default_factory_config
from backend.models.enums import StationId
from backend.optimization.models import OptimizationObjective, InterventionConstraint
from backend.optimization.optimizer import InterventionOptimizer


def test_candidate_generation_and_constraints():
    """Verify constraints prune invalid candidates."""
    config = get_default_factory_config()

    constraint = InterventionConstraint(
        prohibited_stations=[StationId.S1, StationId.S2],
        max_budget=20.0,
    )

    optimizer = InterventionOptimizer(base_config=config, constraint=constraint)
    candidates = optimizer._generate_candidates()

    # S1 and S2 should not have any CYCLE_TIME_REDUCTION actions
    for c in candidates:
        if c.target_station:
            assert c.target_station not in [StationId.S1, StationId.S2]


def test_optimization_returns_result():
    """Verify optimization evaluates candidates and returns a valid result."""
    config = get_default_factory_config()
    # Force S3 to be a massive bottleneck
    config.station_configs[StationId.S3].baseline_cycle_time = 100.0

    optimizer = InterventionOptimizer(
        base_config=config,
        simulation_duration=3600.0,
        seed=42,
        objective=OptimizationObjective(
            risk_reduction_weight=100.0,
            throughput_weight=10.0,
            cost_weight=0.1,
        ),
    )

    result = optimizer.optimize()

    assert result.best_intervention is not None
    assert result.computation_time_ms > 0
    assert len(result.alternative_candidates) >= 0
    # The best score should be the highest among all evaluated
    if result.alternative_candidates:
        assert result.best_intervention.score >= result.alternative_candidates[0].score


def test_constraint_budget_rejection():
    """Candidates exceeding budget should be rejected."""
    config = get_default_factory_config()

    constraint = InterventionConstraint(max_budget=10.0)  # Very tight budget

    optimizer = InterventionOptimizer(
        base_config=config,
        constraint=constraint,
        simulation_duration=600.0,
    )

    result = optimizer.optimize()

    # All cycle-time and most buffer candidates cost > $10, so many should be rejected
    assert result.rejected_count > 0


def test_optimization_deterministic():
    """Same config/seed produces identical results."""
    config = get_default_factory_config()
    config.station_configs[StationId.S4].baseline_cycle_time = 75.0

    kwargs = dict(
        base_config=config,
        simulation_duration=600.0,
        seed=42,
    )

    r1 = InterventionOptimizer(**kwargs).optimize()
    r2 = InterventionOptimizer(**kwargs).optimize()

    assert r1.best_intervention.score == r2.best_intervention.score
    assert r1.best_intervention.action == r2.best_intervention.action
