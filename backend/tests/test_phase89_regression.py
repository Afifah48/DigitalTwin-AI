"""
Phase 8/9 Regression Tests - Throughput Improvement Verification

Enforces:
  1. Cycle-time reduction at a severe bottleneck produces measurable throughput delta.
  2. throughput_delta is always the arithmetic difference - never fabricated.
  3. Optimizer evaluates multiple candidates when budget allows.
  4. Optimizer selects a throughput-improving intervention when one exists.
  5. Zero-magnitude action produces zero throughput/risk delta.
  6. Baseline and counterfactual are deterministic (same seed + duration).
"""

import pytest
from backend.config.factory_config import get_default_factory_config
from backend.counterfactual.models import InterventionType, CounterfactualAction
from backend.counterfactual.simulator import CounterfactualSimulator
from backend.models.enums import StationId
from backend.optimization.models import InterventionConstraint, OptimizationObjective
from backend.optimization.optimizer import InterventionOptimizer


def _sim(config, duration=7200, seed=42):
    return CounterfactualSimulator(base_config=config, simulation_duration=duration, seed=seed)


def test_cycle_time_reduction_changes_simulation_behavior():
    """Large cycle-time reduction at a dominant bottleneck must raise throughput."""
    config = get_default_factory_config()
    config.station_configs[StationId.S5].baseline_cycle_time = 120.0
    result = _sim(config).simulate(CounterfactualAction(
        target_station=StationId.S5,
        action_type=InterventionType.CYCLE_TIME_REDUCTION,
        magnitude=-60.0,
    ))
    assert result.counterfactual_throughput > result.baseline_throughput


def test_throughput_delta_equals_difference():
    """throughput_delta must exactly equal CF - baseline."""
    config = get_default_factory_config()
    config.station_configs[StationId.S2].baseline_cycle_time = 80.0
    result = _sim(config, duration=3600).simulate(CounterfactualAction(
        target_station=StationId.S2,
        action_type=InterventionType.CYCLE_TIME_REDUCTION,
        magnitude=-25.0,
    ))
    expected = result.counterfactual_throughput - result.baseline_throughput
    assert result.throughput_delta == pytest.approx(expected, abs=1e-6)


def test_optimizer_evaluates_multiple_candidates():
    """With a generous budget the optimizer must evaluate at least 3 candidates."""
    config = get_default_factory_config()
    config.station_configs[StationId.S3].baseline_cycle_time = 90.0
    result = InterventionOptimizer(
        base_config=config,
        constraint=InterventionConstraint(max_budget=300.0),
        simulation_duration=600.0,
        seed=42,
    ).optimize()
    total = 1 + len(result.alternative_candidates)
    assert total >= 3, f"Expected >=3 evaluated, got {total}"


def test_optimizer_selects_throughput_improving_intervention():
    """When throughput weight dominates, best intervention must have TP delta >= 0."""
    config = get_default_factory_config()
    config.station_configs[StationId.S6].baseline_cycle_time = 120.0
    result = InterventionOptimizer(
        base_config=config,
        constraint=InterventionConstraint(max_budget=300.0),
        simulation_duration=7200.0,
        seed=42,
        objective=OptimizationObjective(
            risk_reduction_weight=10.0,
            throughput_weight=500.0,
            queue_weight=50.0,
            cost_weight=0.5,
            disruption_weight=5.0,
        ),
    ).optimize()
    assert result.best_intervention is not None
    assert result.best_intervention.simulated_result.throughput_delta >= 0.0


def test_no_fabricated_throughput_on_zero_change():
    """Zero-magnitude action must produce exactly zero throughput and risk delta."""
    config = get_default_factory_config()
    result = _sim(config, duration=600).simulate(CounterfactualAction(
        target_station=StationId.S3,
        action_type=InterventionType.CYCLE_TIME_REDUCTION,
        magnitude=0.0,
    ))
    assert result.throughput_delta == pytest.approx(0.0, abs=1e-6)
    assert result.risk_delta == pytest.approx(0.0, abs=1e-6)


def test_baseline_and_counterfactual_are_deterministic():
    """Running the same action twice must return identical throughput values."""
    config = get_default_factory_config()
    config.station_configs[StationId.S4].baseline_cycle_time = 75.0
    action = CounterfactualAction(
        target_station=StationId.S4,
        action_type=InterventionType.CYCLE_TIME_REDUCTION,
        magnitude=-5.0,
    )
    r1 = _sim(config, duration=1800, seed=99).simulate(action)
    r2 = _sim(config, duration=1800, seed=99).simulate(action)
    assert r1.baseline_throughput == r2.baseline_throughput
    assert r1.counterfactual_throughput == r2.counterfactual_throughput
