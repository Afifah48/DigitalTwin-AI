"""
End-to-End Demonstration of Phase 7 Factory Operational Intelligence & Decision Layer.

Simulates a gradual S3 bearing degradation scenario, runs Phase 4 anomaly detection,
Phase 5 bottleneck flow reasoning, Phase 6 vehicle quality predictions, and generates
the final interpretable FactoryDecision contract at timestamp t.
"""

from __future__ import annotations

import json
from backend.analytics.baseline import calculate_baseline
from backend.data.synthetic_factory import ScenarioType, simulate_factory_run
from backend.app.decision.phase4_adapter import Phase4DecisionAdapter
from backend.app.decision.phase5_adapter import Phase5DecisionAdapter
from backend.app.decision.phase6_adapter import Phase6DecisionAdapter
from backend.app.decision.service import DecisionService
from backend.quality.service import QualityRiskService
from backend.quality.training import generate_vehicle_trajectories


def run_phase7_end_to_end_demo() -> None:
    print("=" * 80)
    print("PHASE 7: FACTORY OPERATIONAL INTELLIGENCE & DECISION LAYER DEMO")
    print("=" * 80)

    # 1. Simulate Factory Scenario (Gradual S3 Bearing Degradation)
    run_id = "demo_s3_degradation"
    print(f"\n[1/4] Simulating factory run with Scenario: {ScenarioType.GRADUAL_S3_DEGRADATION.value}...")
    v_data, gt_list, p4_adapter_q, p5_adapter_q = generate_vehicle_trajectories(
        run_id=run_id,
        scenario=ScenarioType.GRADUAL_S3_DEGRADATION,
        num_vehicles=20,
        steps_per_run=60,
        random_seed=42,
    )

    # 2. Run Phase 6 Vehicle Quality Model
    print("[2/4] Executing Phase 6 QualityRiskService across vehicle trajectories...")
    q_service = QualityRiskService()
    p6_predictions = []
    for v_entry in v_data:
        pred = q_service.predict(
            vehicle_id=v_entry["vehicle_id"],
            vehicle_history=v_entry["observations"],
            as_of_timestamp=v_entry["completed_timestamp"],
            phase4_adapter=p4_adapter_q,
            phase5_adapter=p5_adapter_q,
        )
        p6_predictions.append(pred)

    # 3. Populate Phase 7 Adapters
    print("[3/4] Ingesting multi-phase intelligence into Phase 7 Adapters...")
    p4_dec_adapter = Phase4DecisionAdapter(p4_adapter_q._predictions)
    p5_dec_adapter = Phase5DecisionAdapter(p5_adapter_q._snapshots)
    p6_dec_adapter = Phase6DecisionAdapter(p6_predictions)

    # Convert vehicle observations to latest raw telemetry format
    telemetry_snaps = []
    for v in v_data:
        obs_map = {obs.station_id: {
            "station_id": obs.station_id,
            "cycle_time": obs.cycle_time,
            "cycle_time_delta": obs.cycle_time_delta,
            "vibration": obs.vibration,
            "temperature": obs.temperature,
            "motor_current": obs.motor_current,
            "current_variance": obs.current_variance,
            "machine_state": obs.machine_state,
            "buffer_occupancy": obs.buffer_occupancy,
        } for obs in v["observations"]}
        telemetry_snaps.append({
            "timestamp": v["completed_timestamp"],
            "stations": obs_map,
            "buffers": {"B2": {"occupancy": 9.2}, "B3": {"occupancy": 0.5}},
        })

    # 4. Generate Factory Decision at Critical Timestamp
    t_decision = v_data[-1]["completed_timestamp"]
    print(f"[4/4] Generating FactoryDecision at timestamp t = {t_decision:.2f}...")

    decision_service = DecisionService(
        phase4_adapter=p4_dec_adapter,
        phase5_adapter=p5_dec_adapter,
        phase6_adapter=p6_dec_adapter,
    )

    decision = decision_service.analyze(
        timestamp=t_decision,
        telemetry_snapshots=telemetry_snaps,
    )

    print("\n" + "=" * 80)
    print("GENERATED FACTORY DECISION CONTRACT")
    print("=" * 80)
    print(json.dumps(decision.to_dict(), indent=2))
    print("=" * 80)


if __name__ == "__main__":
    run_phase7_end_to_end_demo()
