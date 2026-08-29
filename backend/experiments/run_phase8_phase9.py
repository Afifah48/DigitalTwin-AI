from backend.config.factory_config import get_default_factory_config
from backend.models.enums import StationId
from backend.optimization.models import OptimizationObjective, InterventionConstraint
from backend.optimization.optimizer import InterventionOptimizer


def main():
    print("================================================================================")
    print(" PHASE 8 & 9 - COUNTERFACTUAL SIMULATION & INTERVENTION OPTIMIZATION")
    print("================================================================================")

    # 1. Setup a baseline factory configuration with an induced bottleneck
    config = get_default_factory_config()
    print("\n[Baseline] Inducing a bottleneck at S4 (POWERTRAIN)...")
    config.station_configs[StationId.S4].baseline_cycle_time = 75.0  # severely slow

    # 2. Setup optimization constraints and objectives
    constraint = InterventionConstraint(max_budget=300.0)
    objective = OptimizationObjective(
        risk_reduction_weight=100.0,
        throughput_weight=500.0,
        queue_weight=100.0,
        cost_weight=0.5,
        disruption_weight=20.0
    )

    optimizer = InterventionOptimizer(
        base_config=config,
        objective=objective,
        constraint=constraint,
        simulation_duration=7200.0,  # simulate 2 hours to allow throughput to stabilize
        seed=42
    )

    print("\n[Optimization] Running Phase 8 Counterfactuals across Candidate Grid...")
    result = optimizer.optimize()

    print(f"\nOptimization completed in {result.computation_time_ms:.0f} ms.")
    print(f"Evaluated candidates: {len(result.alternative_candidates) + 1}")
    print(f"Rejected candidates: {result.rejected_count} (Exceeded constraints)")

    if result.best_intervention:
        best = result.best_intervention
        action = best.action
        cf_res = best.simulated_result
        
        print("\n================================================================================")
        print(" RECOMMENDED INTERVENTION (PHASE 9)")
        print("================================================================================")
        print(f" Action Type : {action.action_type.name}")
        print(f" Target      : {action.target_station.value if action.target_station else action.target_buffer.value}")
        print(f" Magnitude   : {action.magnitude}")
        print(f" Description : {action.description}")
        print(f" Cost        : ${action.cost:.2f}")
        
        print("\n--------------------------------------------------------------------------------")
        print(" EXPECTED COUNTERFACTUAL IMPACT (PHASE 8)")
        print("--------------------------------------------------------------------------------")
        print(f" Score       : {best.score:.2f}")
        print(f" Justification: {best.justification}")
        print(f" Baseline Risk: {cf_res.baseline_risk:.4f} -> {cf_res.counterfactual_risk:.4f} (Delta: {cf_res.risk_delta:.4f})")
        
        tp_percent = (cf_res.throughput_delta / cf_res.baseline_throughput * 100.0) if cf_res.baseline_throughput > 0 else 0.0
        print(f" Throughput   : {cf_res.baseline_throughput:.1f} -> {cf_res.counterfactual_throughput:.1f} UPH (Delta: {cf_res.throughput_delta:+.1f} UPH, {tp_percent:+.1f}%)")
        print(f" Queue/WIP    : {cf_res.baseline_total_queue} -> {cf_res.counterfactual_total_queue} units (Delta: {cf_res.queue_delta:+})")
        print(f" Affected Stations: {', '.join([s.value for s in cf_res.affected_stations])}")
        
        mig_status = "YES" if cf_res.bottleneck_migrated else "NO"
        print(f" Bottleneck Migration: {mig_status}")
        if cf_res.bottleneck_migrated:
            base_bn = cf_res.baseline_bottleneck_station.value if cf_res.baseline_bottleneck_station else "None"
            cf_bn = cf_res.counterfactual_bottleneck_station.value if cf_res.counterfactual_bottleneck_station else "None"
            print(f"   Shifted from {base_bn} to {cf_bn}")

    print("\n================================================================================")
    print(" ALTERNATIVE CANDIDATES")
    print("================================================================================")
    for i, alt in enumerate(result.alternative_candidates[:3]):
        print(f"#{i+1}: {alt.action.description} (Score: {alt.score:.2f})")
        print(f"    {alt.justification}")


if __name__ == "__main__":
    main()
