"""
Comprehensive Unit and Integration Test Suite for Phase 7 Factory Decision Layer.

Tests 26 essential capabilities including multi-phase aggregation, severity calculation,
root-cause hypotheses, spatial impact, operational recommendations, auditability,
and strict zero future data leakage.
"""

from __future__ import annotations

import copy
import json
import os
import unittest
import numpy as np

from backend.app.decision.aggregation import FactoryEvidenceAggregator, FactorySnapshotContext
from backend.app.decision.audit import DecisionAuditLogger
from backend.app.decision.impact import FactoryImpactAnalyzer
from backend.app.decision.phase4_adapter import Phase4DecisionAdapter
from backend.app.decision.phase5_adapter import Phase5DecisionAdapter
from backend.app.decision.phase6_adapter import Phase6DecisionAdapter
from backend.app.decision.recommendations import FactoryRecommendationEngine
from backend.app.decision.root_cause import FactoryRootCauseEngine
from backend.app.decision.schemas import (
    ActionPriority,
    ActionType,
    DecisionEvidenceItem,
    FactoryDecision,
    FactoryStatus,
    ImpactSummary,
    PropagationDirection,
    RecommendedActionItem,
    RootCauseHypothesis,
)
from backend.app.decision.service import DecisionService
from backend.app.decision.severity import FactorySeverityEngine
from backend.quality.schemas import VehicleRiskPrediction


class TestDecisionLayerSubsystem(unittest.TestCase):
    """Phase 7 Decision & Operational Intelligence Test Suite."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.base_time = 1700000000.0

        # Nominal Telemetry Fixture
        cls.nominal_telemetry = [
            {
                "timestamp": cls.base_time + (step * 5.0),
                "stations": {
                    f"S{i}": {
                        "station_id": f"S{i}",
                        "cycle_time": 50.0,
                        "cycle_time_delta": 0.0,
                        "vibration": 0.08,
                        "temperature": 60.0,
                        "motor_current": 4.5,
                        "current_variance": 0.04,
                        "machine_state": "RUNNING",
                        "buffer_occupancy": 3.0,
                    }
                    for i in range(1, 7)
                },
                "buffers": {f"B{k}": {"occupancy": 3.0, "capacity": 10.0} for k in range(1, 6)},
            }
            for step in range(20)
        ]

        # Degraded S3 Telemetry Fixture (t=100)
        cls.degraded_s3_telemetry = copy.deepcopy(cls.nominal_telemetry)
        cls.degraded_s3_telemetry.append({
            "timestamp": cls.base_time + 105.0,
            "stations": {
                "S1": {"station_id": "S1", "cycle_time": 45.0, "vibration": 0.08, "machine_state": "RUNNING", "buffer_occupancy": 3.0},
                "S2": {"station_id": "S2", "cycle_time": 48.0, "vibration": 0.09, "machine_state": "BLOCKED", "buffer_occupancy": 9.2},
                "S3": {
                    "station_id": "S3",
                    "cycle_time": 72.0,
                    "cycle_time_delta": 18.0,
                    "vibration": 0.42,
                    "temperature": 88.0,
                    "motor_current": 9.5,
                    "current_variance": 0.48,
                    "machine_state": "WARNING",
                    "buffer_occupancy": 9.2,
                },
                "S4": {"station_id": "S4", "cycle_time": 50.0, "vibration": 0.09, "machine_state": "STARVED", "buffer_occupancy": 0.5},
                "S5": {"station_id": "S5", "cycle_time": 46.0, "vibration": 0.08, "machine_state": "RUNNING", "buffer_occupancy": 3.0},
                "S6": {"station_id": "S6", "cycle_time": 44.0, "vibration": 0.07, "machine_state": "RUNNING", "buffer_occupancy": 3.0},
            },
            "buffers": {
                "B1": {"occupancy": 3.0, "capacity": 10.0},
                "B2": {"occupancy": 9.2, "capacity": 10.0},
                "B3": {"occupancy": 0.5, "capacity": 10.0},
                "B4": {"occupancy": 3.0, "capacity": 10.0},
                "B5": {"occupancy": 3.0, "capacity": 10.0},
            },
        })

    # 1. Normal Factory Operation Test
    def test_01_normal_factory(self) -> None:
        service = DecisionService()
        decision = service.analyze(
            timestamp=self.base_time + 50.0,
            telemetry_snapshots=self.nominal_telemetry,
        )
        self.assertEqual(decision.factory_status, "NOMINAL")
        self.assertLess(decision.overall_risk, 0.20)
        self.assertEqual(len(decision.affected_stations), 0)
        self.assertEqual(decision.recommended_actions[0].action, "MONITOR")

    # 2. Single Station Anomaly Test
    def test_02_single_anomaly(self) -> None:
        p4 = Phase4DecisionAdapter([{
            "station_id": "S1",
            "timestamp": self.base_time + 50.0,
            "anomaly_score": 0.72,
            "severity": "HIGH",
            "detected": True,
            "top_signals": ["vibration"],
        }])
        service = DecisionService(phase4_adapter=p4)
        decision = service.analyze(
            timestamp=self.base_time + 50.0,
            telemetry_snapshots=self.nominal_telemetry,
        )
        self.assertIn(decision.factory_status, ("LOW", "MEDIUM"))
        self.assertIn("S1", decision.affected_stations)

    # 3. Anomaly Without Bottleneck (Isolated Transient)
    def test_03_anomaly_without_bottleneck(self) -> None:
        p4 = Phase4DecisionAdapter([{
            "station_id": "S5",
            "timestamp": self.base_time + 50.0,
            "anomaly_score": 0.70,
            "severity": "MEDIUM",
            "detected": True,
        }])
        service = DecisionService(phase4_adapter=p4)
        decision = service.analyze(
            timestamp=self.base_time + 50.0,
            telemetry_snapshots=self.nominal_telemetry,
        )
        # Should not jump to CRITICAL without bottleneck/flow blockage
        self.assertNotEqual(decision.factory_status, "CRITICAL")
        self.assertEqual(decision.impact.propagation_direction, "NONE")

    # 4. Persistent Bottleneck Test
    def test_04_persistent_bottleneck(self) -> None:
        p5 = Phase5DecisionAdapter([
            {"timestamp": self.base_time + (i * 5.0), "predicted_bottleneck_station": "S3", "bottleneck_risk": 0.85}
            for i in range(10)
        ])
        service = DecisionService(phase5_adapter=p5)
        decision = service.analyze(
            timestamp=self.base_time + 50.0,
            telemetry_snapshots=self.nominal_telemetry,
        )
        self.assertIn("S3", decision.affected_stations)
        self.assertGreater(decision.overall_risk, 0.25)

    # 5. Upstream Blocking Propagation Test
    def test_05_upstream_blocking(self) -> None:
        p5 = Phase5DecisionAdapter([{
            "timestamp": self.base_time + 105.0,
            "predicted_bottleneck_station": "S3",
            "bottleneck_risk": 0.90,
            "highest_buffer_pressure": "B2",
        }])
        service = DecisionService(phase5_adapter=p5)
        decision = service.analyze(
            timestamp=self.base_time + 105.0,
            telemetry_snapshots=self.degraded_s3_telemetry,
        )
        self.assertIn(decision.impact.propagation_direction, ("UPSTREAM_BLOCKING", "BIDIRECTIONAL"))
        self.assertIn("S2", decision.impact.upstream_blocked_stations)

    # 6. Downstream Starvation Propagation Test
    def test_06_downstream_starvation(self) -> None:
        p5 = Phase5DecisionAdapter([
            {"timestamp": self.base_time + (i * 5.0), "predicted_bottleneck_station": "S3", "bottleneck_risk": 0.88}
            for i in range(10)
        ])
        service = DecisionService(phase5_adapter=p5)
        decision = service.analyze(
            timestamp=self.base_time + 105.0,
            telemetry_snapshots=self.degraded_s3_telemetry,
        )
        self.assertIn("S4", decision.impact.downstream_starved_stations)

    # 7. Bidirectional Flow Propagation Test
    def test_07_bidirectional_propagation(self) -> None:
        p5 = Phase5DecisionAdapter([
            {
                "timestamp": self.base_time + (i * 5.0),
                "predicted_bottleneck_station": "S3",
                "bottleneck_risk": 0.90,
                "highest_buffer_pressure": "B2",
            }
            for i in range(10)
        ])
        service = DecisionService(phase5_adapter=p5)
        decision = service.analyze(
            timestamp=self.base_time + 105.0,
            telemetry_snapshots=self.degraded_s3_telemetry,
        )
        self.assertEqual(decision.impact.propagation_direction, "BIDIRECTIONAL")

    # 8. High Vehicle Quality Risk Test
    def test_08_high_vehicle_quality_risk(self) -> None:
        p6 = Phase6DecisionAdapter([
            VehicleRiskPrediction(
                vehicle_id="V_DEF_99",
                timestamp=self.base_time + 50.0,
                risk_score=92.0,
                defect_probability=0.92,
                quality_exposure="HIGH",
                recommended_action="QA_INSPECTION",
            )
        ])
        service = DecisionService(phase6_adapter=p6)
        decision = service.analyze(
            timestamp=self.base_time + 50.0,
            telemetry_snapshots=self.nominal_telemetry,
        )
        self.assertIn("V_DEF_99", decision.affected_vehicles)
        self.assertTrue(any(a.action == "QA_INSPECTION" for a in decision.recommended_actions))

    # 9. Multiple Affected Vehicles
    def test_09_multiple_affected_vehicles(self) -> None:
        p6 = Phase6DecisionAdapter([
            VehicleRiskPrediction(
                vehicle_id=f"V_DEF_{i}",
                timestamp=self.base_time + (i * 10.0),
                risk_score=85.0,
                defect_probability=0.85,
                quality_exposure="HIGH",
                recommended_action="QA_INSPECTION",
            )
            for i in range(1, 4)
        ])
        service = DecisionService(phase6_adapter=p6)
        decision = service.analyze(
            timestamp=self.base_time + 50.0,
            telemetry_snapshots=self.nominal_telemetry,
        )
        self.assertEqual(len(decision.affected_vehicles), 3)
        self.assertEqual(decision.impact.high_risk_vehicle_count, 3)

    # 10. Combined Incident (Anomaly + Bottleneck + Quality Defect)
    def test_10_combined_incident(self) -> None:
        p4 = Phase4DecisionAdapter([{
            "station_id": "S3",
            "timestamp": self.base_time + 105.0,
            "anomaly_score": 0.95,
            "severity": "HIGH",
            "detected": True,
            "top_signals": ["vibration", "current_variance"],
        }])
        p5 = Phase5DecisionAdapter([
            {"timestamp": self.base_time + (i * 5.0), "predicted_bottleneck_station": "S3", "bottleneck_risk": 0.92, "highest_buffer_pressure": "B2"}
            for i in range(22)
        ])
        p6 = Phase6DecisionAdapter([
            VehicleRiskPrediction(
                vehicle_id="V_INCIDENT_01",
                timestamp=self.base_time + 105.0,
                risk_score=94.0,
                defect_probability=0.94,
                quality_exposure="HIGH",
                recommended_action="QA_INSPECTION",
            )
        ])
        service = DecisionService(phase4_adapter=p4, phase5_adapter=p5, phase6_adapter=p6)
        decision = service.analyze(
            timestamp=self.base_time + 105.0,
            telemetry_snapshots=self.degraded_s3_telemetry,
        )
        self.assertEqual(decision.factory_status, "CRITICAL")
        self.assertGreater(decision.overall_risk, 0.75)
        self.assertTrue(any(rc.category == "MECHANICAL_DEGRADATION" for rc in decision.root_causes))
        self.assertTrue(any(a.action == "ESCALATE" for a in decision.recommended_actions))
        self.assertTrue(any(a.action == "INSPECT_MACHINE" for a in decision.recommended_actions))
        self.assertTrue(any(a.action == "QA_INSPECTION" for a in decision.recommended_actions))

    # 11. Root-Cause Evidence Generation
    def test_11_root_cause_evidence_generation(self) -> None:
        p4 = Phase4DecisionAdapter([{
            "station_id": "S3",
            "timestamp": self.base_time + 105.0,
            "anomaly_score": 0.95,
            "severity": "HIGH",
            "detected": True,
        }])
        service = DecisionService(phase4_adapter=p4)
        decision = service.analyze(
            timestamp=self.base_time + 105.0,
            telemetry_snapshots=self.degraded_s3_telemetry,
        )
        self.assertGreater(len(decision.root_causes), 0)
        top_rc = decision.root_causes[0]
        self.assertGreater(len(top_rc.supporting_evidence), 0)
        self.assertIsNotNone(top_rc.supporting_evidence[0].signal)
        self.assertIsNotNone(top_rc.supporting_evidence[0].source)

    # 12. Recommendation Generation
    def test_12_recommendation_generation(self) -> None:
        service = DecisionService()
        decision = service.analyze(self.base_time + 50.0, self.nominal_telemetry)
        self.assertEqual(len(decision.recommended_actions), 1)
        self.assertEqual(decision.recommended_actions[0].action, "MONITOR")
        self.assertEqual(decision.recommended_actions[0].priority, "LOW")

    # 13. Confidence Handling
    def test_13_confidence_handling(self) -> None:
        service = DecisionService()
        decision = service.analyze(self.base_time + 50.0, self.nominal_telemetry)
        self.assertEqual(decision.confidence, 1.0)

    # 14. All Stations Participating
    def test_14_all_stations_participating(self) -> None:
        service = DecisionService()
        decision = service.analyze(self.base_time + 50.0, self.nominal_telemetry)
        context = service.aggregator.aggregate_context(self.base_time + 50.0, self.nominal_telemetry)
        self.assertEqual(set(context.stations.keys()), {"S1", "S2", "S3", "S4", "S5", "S6"})

    # 15. Missing Phase 4 Graceful Fallback
    def test_15_missing_phase4_information(self) -> None:
        service = DecisionService(phase4_adapter=Phase4DecisionAdapter())
        decision = service.analyze(self.base_time + 50.0, self.nominal_telemetry)
        self.assertIsNotNone(decision)
        self.assertEqual(decision.factory_status, "NOMINAL")

    # 16. Missing Phase 5 Graceful Fallback
    def test_16_missing_phase5_information(self) -> None:
        service = DecisionService(phase5_adapter=Phase5DecisionAdapter())
        decision = service.analyze(self.base_time + 50.0, self.nominal_telemetry)
        self.assertIsNotNone(decision)
        self.assertEqual(decision.factory_status, "NOMINAL")

    # 17. Missing Phase 6 Graceful Fallback
    def test_17_missing_phase6_information(self) -> None:
        service = DecisionService(phase6_adapter=Phase6DecisionAdapter())
        decision = service.analyze(self.base_time + 50.0, self.nominal_telemetry)
        self.assertIsNotNone(decision)
        self.assertEqual(len(decision.affected_vehicles), 0)

    # 18. Future Telemetry Zero-Leakage
    def test_18_future_telemetry_leakage(self) -> None:
        t_cutoff = self.base_time + 50.0
        service = DecisionService()

        # Decision 1 with data <= t_cutoff
        dec_1 = service.analyze(t_cutoff, self.nominal_telemetry)

        # Future modified telemetry strictly after t_cutoff
        future_telemetry = copy.deepcopy(self.nominal_telemetry)
        future_telemetry.append({
            "timestamp": t_cutoff + 500.0,
            "stations": {
                "S3": {"station_id": "S3", "vibration": 0.99, "cycle_time": 100.0, "machine_state": "DOWN"}
            }
        })

        # Decision 2
        dec_2 = service.analyze(t_cutoff, future_telemetry)
        self.assertEqual(dec_1.factory_status, dec_2.factory_status)
        self.assertAlmostEqual(dec_1.overall_risk, dec_2.overall_risk, places=5)

    # 19. Future Phase 4 Zero-Leakage
    def test_19_future_phase4_leakage(self) -> None:
        t_cutoff = self.base_time + 50.0
        p4 = Phase4DecisionAdapter([{
            "station_id": "S1", "timestamp": t_cutoff, "anomaly_score": 0.10, "detected": False
        }])
        service = DecisionService(phase4_adapter=p4)
        dec_1 = service.analyze(t_cutoff, self.nominal_telemetry)

        # Ingest future alarm at t=999
        p4.ingest_prediction({"station_id": "S1", "timestamp": t_cutoff + 999.0, "anomaly_score": 0.99, "detected": True})
        dec_2 = service.analyze(t_cutoff, self.nominal_telemetry)
        self.assertEqual(dec_1.factory_status, dec_2.factory_status)
        self.assertEqual(dec_1.overall_risk, dec_2.overall_risk)

    # 20. Future Phase 5 Zero-Leakage
    def test_20_future_phase5_leakage(self) -> None:
        t_cutoff = self.base_time + 50.0
        p5 = Phase5DecisionAdapter([{"timestamp": t_cutoff, "predicted_bottleneck_station": None, "bottleneck_risk": 0.05}])
        service = DecisionService(phase5_adapter=p5)
        dec_1 = service.analyze(t_cutoff, self.nominal_telemetry)

        # Ingest future bottleneck at t=999
        p5.ingest_snapshot({"timestamp": t_cutoff + 999.0, "predicted_bottleneck_station": "S3", "bottleneck_risk": 0.99})
        dec_2 = service.analyze(t_cutoff, self.nominal_telemetry)
        self.assertEqual(dec_1.factory_status, dec_2.factory_status)
        self.assertEqual(dec_1.overall_risk, dec_2.overall_risk)

    # 21. Future Phase 6 Zero-Leakage
    def test_21_future_phase6_leakage(self) -> None:
        t_cutoff = self.base_time + 50.0
        p6 = Phase6DecisionAdapter([
            VehicleRiskPrediction(vehicle_id="V1", timestamp=t_cutoff, risk_score=10.0, defect_probability=0.10, quality_exposure="LOW", recommended_action="PASS_MONITOR")
        ])
        service = DecisionService(phase6_adapter=p6)
        dec_1 = service.analyze(t_cutoff, self.nominal_telemetry)

        # Ingest future defective vehicle at t=999
        p6.ingest_prediction(
            VehicleRiskPrediction(vehicle_id="V_FUT", timestamp=t_cutoff + 999.0, risk_score=99.0, defect_probability=0.99, quality_exposure="HIGH", recommended_action="QA_INSPECTION")
        )
        dec_2 = service.analyze(t_cutoff, self.nominal_telemetry)
        self.assertEqual(dec_1.affected_vehicles, dec_2.affected_vehicles)
        self.assertEqual(dec_1.overall_risk, dec_2.overall_risk)

    # 22. Deterministic Output
    def test_22_deterministic_output(self) -> None:
        service = DecisionService()
        dec_1 = service.analyze(self.base_time + 50.0, self.nominal_telemetry)
        dec_2 = service.analyze(self.base_time + 50.0, self.nominal_telemetry)
        d1 = dec_1.to_dict()
        d2 = dec_2.to_dict()
        d1.get("audit_trail", {}).pop("execution_timestamp", None)
        d2.get("audit_trail", {}).pop("execution_timestamp", None)
        self.assertEqual(d1, d2)

    # 23. Schema Validation
    def test_23_schema_validation(self) -> None:
        dec = FactoryDecision(
            timestamp=self.base_time,
            factory_status="NOMINAL",
            overall_risk=0.12,
            primary_issue=None,
        )
        d = dec.to_dict()
        self.assertEqual(d["factory_status"], "NOMINAL")
        self.assertEqual(d["overall_risk"], 0.12)

        with self.assertRaises(ValueError):
            FactoryDecision(
                timestamp=self.base_time,
                factory_status="INVALID_STATUS",
                overall_risk=0.50,
                primary_issue=None,
            )

    # 24. Configuration Loading
    def test_24_configuration_loading(self) -> None:
        service = DecisionService()
        self.assertIn("severity_thresholds", service.config)
        self.assertIn("root_cause_thresholds", service.config)

    # 25. Audit Traceability
    def test_25_audit_traceability(self) -> None:
        service = DecisionService()
        decision = service.analyze(self.base_time + 50.0, self.nominal_telemetry)
        self.assertIn("decision_timestamp", decision.audit_trail)
        self.assertIn("evaluated_stations_count", decision.audit_trail)
        self.assertIn("assigned_status", decision.audit_trail)

    # 26. CRITICAL ZERO-LEAKAGE VERIFICATION TEST
    def test_26_critical_zero_leakage(self) -> None:
        """
        Critical Zero-Leakage Test:
        Decision at t=200 must be mathematically IDENTICAL before and after injecting
        catastrophic failure data at t=500 across telemetry, Phase 4, Phase 5, and Phase 6.
        """
        t_eval = self.base_time + 200.0

        p4 = Phase4DecisionAdapter([{
            "station_id": "S1", "timestamp": t_eval, "anomaly_score": 0.12, "severity": "LOW", "detected": False
        }])
        p5 = Phase5DecisionAdapter([{
            "timestamp": t_eval, "predicted_bottleneck_station": None, "bottleneck_risk": 0.05, "propagation_risk": 0.05
        }])
        p6 = Phase6DecisionAdapter([
            VehicleRiskPrediction(vehicle_id="V_NORM", timestamp=t_eval, risk_score=12.0, defect_probability=0.12, quality_exposure="LOW", recommended_action="PASS_MONITOR")
        ])

        service = DecisionService(phase4_adapter=p4, phase5_adapter=p5, phase6_adapter=p6)
        decision_1 = service.analyze(
            timestamp=t_eval,
            telemetry_snapshots=self.nominal_telemetry,
        )

        # Add severe future events at t = t_eval + 300.0 (t = 500)
        future_telemetry = copy.deepcopy(self.nominal_telemetry)
        future_telemetry.append({
            "timestamp": t_eval + 300.0,
            "stations": {
                "S3": {"station_id": "S3", "vibration": 0.99, "machine_state": "FAULT", "motor_current": 45.0}
            }
        })
        p4.ingest_prediction({
            "station_id": "S3", "timestamp": t_eval + 300.0, "anomaly_score": 0.99, "severity": "CRITICAL", "detected": True
        })
        p5.ingest_snapshot({
            "timestamp": t_eval + 300.0, "predicted_bottleneck_station": "S3", "bottleneck_risk": 0.99, "propagation_risk": 0.95
        })
        p6.ingest_prediction(
            VehicleRiskPrediction(vehicle_id="V_CRITICAL", timestamp=t_eval + 300.0, risk_score=99.0, defect_probability=0.99, quality_exposure="HIGH", recommended_action="QA_INSPECTION")
        )

        decision_2 = service.analyze(
            timestamp=t_eval,
            telemetry_snapshots=future_telemetry,
        )

        # Assert exact equivalence at t_eval
        self.assertEqual(decision_1.factory_status, decision_2.factory_status)
        self.assertAlmostEqual(decision_1.overall_risk, decision_2.overall_risk, places=5)
        self.assertEqual(decision_1.affected_stations, decision_2.affected_stations)
        self.assertEqual(decision_1.affected_vehicles, decision_2.affected_vehicles)
        self.assertEqual(len(decision_1.recommended_actions), len(decision_2.recommended_actions))
        self.assertEqual(decision_1.recommended_actions[0].action, decision_2.recommended_actions[0].action)


if __name__ == "__main__":
    unittest.main()
