"""
Comprehensive Unit and Integration Test Suite for Phase 6 Vehicle Quality Prediction.

Tests 26 essential capabilities including temporal filtering, zero-leakage protection,
adapters, preprocessing, models (Logistic Regression, Random Forest, XGBoost),
probability calibration, risk classification, SHAP explanations, and deterministic inference.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
import unittest
import numpy as np

from backend.quality.calibration import (
    QualityProbabilityCalibrator,
    calculate_calibration_error,
)
from backend.quality.explain import QualityExplainer
from backend.quality.features import (
    QUALITY_FEATURE_NAMES,
    VehicleFeaturePreprocessor,
    extract_vehicle_features,
    feature_dict_to_array,
)
from backend.quality.models import (
    LogisticRegressionQualityModel,
    RandomForestQualityModel,
    XGBoostQualityModel,
)
from backend.quality.phase4_adapter import Phase4Adapter
from backend.quality.phase5_adapter import BottleneckSnapshot, Phase5Adapter
from backend.quality.risk import (
    DEFAULT_RISK_POLICY,
    QualityRiskPolicy,
    compute_vehicle_risk,
)
from backend.quality.schemas import (
    DefectSeverity,
    QualityExposureLevel,
    RecommendedAction,
    VehicleDefectGroundTruth,
    VehicleObservation,
    VehicleRiskPrediction,
)
from backend.quality.service import QualityRiskService
from backend.quality.temporal import filter_by_timestamp, validate_zero_leakage


class TestQualityPredictionSubsystem(unittest.TestCase):
    """Phase 6 Comprehensive Test Suite."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.test_dir = tempfile.mkdtemp()
        cls.base_time = 1700000000.0

        # Create deterministic synthetic normal and defective vehicle histories
        cls.normal_history = [
            VehicleObservation(
                vehicle_id="V_NORM_001",
                station_id=f"S{i}",
                timestamp=cls.base_time + (i * 50.0),
                vehicle_model="Sedan",
                vehicle_variant="Base",
                duration=50.0,
                cycle_time=50.0,
                cycle_time_delta=0.0,
                queue_length=2,
                buffer_occupancy=3.0,
                temperature=60.0 + i,
                vibration=0.08,
                motor_current=4.5,
                current_variance=0.04,
                machine_state="RUNNING",
            )
            for i in range(1, 7)
        ]

        cls.defective_history = [
            VehicleObservation(
                vehicle_id="V_DEF_001",
                station_id="S1",
                timestamp=cls.base_time + 50.0,
                vehicle_model="SUV",
                vehicle_variant="Premium",
                duration=50.0,
                cycle_time=50.0,
                cycle_time_delta=0.0,
                queue_length=2,
                buffer_occupancy=3.0,
                temperature=61.0,
                vibration=0.08,
                motor_current=4.5,
                current_variance=0.04,
                machine_state="RUNNING",
            ),
            VehicleObservation(
                vehicle_id="V_DEF_001",
                station_id="S2",
                timestamp=cls.base_time + 100.0,
                vehicle_model="SUV",
                vehicle_variant="Premium",
                duration=52.0,
                cycle_time=52.0,
                cycle_time_delta=1.0,
                queue_length=3,
                buffer_occupancy=4.0,
                temperature=63.0,
                vibration=0.10,
                motor_current=4.9,
                current_variance=0.06,
                machine_state="RUNNING",
            ),
            VehicleObservation(
                vehicle_id="V_DEF_001",
                station_id="S3",
                timestamp=cls.base_time + 175.0,
                vehicle_model="SUV",
                vehicle_variant="Premium",
                duration=75.0,  # Slow cycle time
                cycle_time=75.0,
                cycle_time_delta=21.0,
                queue_length=9,
                buffer_occupancy=9.2,
                temperature=88.0,  # High temperature
                vibration=0.45,    # High vibration
                motor_current=9.8,
                current_variance=0.52,  # Severe variance
                machine_state="WARNING",
                torque=14.5,
            ),
        ]

        # Phase 4 and Phase 5 adapter fixtures
        cls.p4_adapter = Phase4Adapter([
            {
                "station_id": "S3",
                "timestamp": cls.base_time + 170.0,
                "anomaly_score": 0.94,
                "severity": "HIGH",
                "detected": True,
                "lead_time_if_known": 180.0,
                "top_signals": ["vibration", "current_variance"],
            }
        ])

        cls.p5_adapter = Phase5Adapter([
            BottleneckSnapshot(
                timestamp=cls.base_time + 170.0,
                predicted_bottleneck_station="S3",
                bottleneck_risk=0.92,
                propagation_risk=0.75,
                station_ranking=[("S3", 0.95)],
            )
        ])

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # 1. Normal Vehicle Test
    def test_01_normal_vehicle(self) -> None:
        feats = extract_vehicle_features(
            vehicle_id="V_NORM_001",
            vehicle_history=self.normal_history,
            as_of_timestamp=self.base_time + 400.0,
            phase4_adapter=Phase4Adapter(),
            phase5_adapter=Phase5Adapter(),
        )
        self.assertEqual(feats["model_Sedan"], 1.0)
        self.assertEqual(feats["variant_Base"], 1.0)
        self.assertLess(feats["vibration_max"], 0.15)
        self.assertEqual(feats["phase4_anomalies_detected_count"], 0)

    # 2. Defective Vehicle Fixture Test
    def test_02_defective_vehicle_fixture(self) -> None:
        feats = extract_vehicle_features(
            vehicle_id="V_DEF_001",
            vehicle_history=self.defective_history,
            as_of_timestamp=self.base_time + 200.0,
            phase4_adapter=self.p4_adapter,
            phase5_adapter=self.p5_adapter,
        )
        self.assertEqual(feats["model_SUV"], 1.0)
        self.assertEqual(feats["variant_Premium"], 1.0)
        self.assertGreater(feats["vibration_max"], 0.40)
        self.assertGreater(feats["phase4_anomaly_score_max"], 0.80)
        self.assertGreater(feats["number_of_abnormal_events"], 0)

    # 3. Vehicle-Level Aggregation
    def test_03_vehicle_level_aggregation(self) -> None:
        feats = extract_vehicle_features(
            vehicle_id="V_DEF_001",
            vehicle_history=self.defective_history,
            as_of_timestamp=self.base_time + 200.0,
        )
        self.assertEqual(feats["stations_visited_count"], 3.0)
        self.assertAlmostEqual(feats["station_exposure_duration"], 50.0 + 52.0 + 75.0)

    # 4. Categorical Feature Encoding
    def test_04_categorical_features(self) -> None:
        feats = extract_vehicle_features(
            vehicle_id="V_CAT",
            vehicle_history=[
                {"station_id": "S1", "timestamp": self.base_time + 10, "vehicle_model": "Truck", "vehicle_variant": "EV"}
            ],
            as_of_timestamp=self.base_time + 20,
        )
        self.assertEqual(feats["model_Truck"], 1.0)
        self.assertEqual(feats["model_Sedan"], 0.0)
        self.assertEqual(feats["variant_EV"], 1.0)
        self.assertEqual(feats["variant_Base"], 0.0)

    # 5. Numerical Feature Extraction
    def test_05_numerical_features(self) -> None:
        feats = extract_vehicle_features("V1", self.normal_history, self.base_time + 400.0)
        arr = feature_dict_to_array(feats, QUALITY_FEATURE_NAMES)
        self.assertEqual(len(arr), len(QUALITY_FEATURE_NAMES))
        self.assertTrue(np.all(np.isfinite(arr)))

    # 6. Missing Values Graceful Handling
    def test_06_missing_values(self) -> None:
        history_missing = [
            {"station_id": "S1", "timestamp": self.base_time + 10, "temperature": None, "vibration": None, "motor_current": None}
        ]
        feats = extract_vehicle_features("V_MISS", history_missing, self.base_time + 20)
        self.assertIsNotNone(feats["vibration_mean"])
        self.assertIsNotNone(feats["temperature_mean"])
        arr = feature_dict_to_array(feats, QUALITY_FEATURE_NAMES)
        self.assertFalse(np.isnan(arr).any())

    # 7. Temporal Filtering Before Aggregation
    def test_07_temporal_filtering(self) -> None:
        records = [
            {"timestamp": 100.0, "val": 1},
            {"timestamp": 200.0, "val": 2},
            {"timestamp": 300.0, "val": 3},
        ]
        filtered = filter_by_timestamp(records, as_of_timestamp=200.0)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[-1]["timestamp"], 200.0)

    # 8. Future Telemetry Zero-Leakage
    def test_08_future_telemetry_leakage(self) -> None:
        t_cutoff = self.base_time + 120.0  # Before S3
        feats_before = extract_vehicle_features("V_DEF_001", self.defective_history, as_of_timestamp=t_cutoff)

        # Append future records at t=999
        future_history = copy.deepcopy(self.defective_history)
        future_history.append(
            VehicleObservation(
                vehicle_id="V_DEF_001",
                station_id="S4",
                timestamp=self.base_time + 999.0,
                vibration=0.99,
            )
        )
        feats_after = extract_vehicle_features("V_DEF_001", future_history, as_of_timestamp=t_cutoff)

        for k in QUALITY_FEATURE_NAMES:
            self.assertEqual(feats_before[k], feats_after[k], f"Feature {k} leaked future telemetry!")

    # 9. Future Phase 4 Zero-Leakage
    def test_09_future_phase4_leakage(self) -> None:
        p4 = Phase4Adapter()
        p4.ingest_prediction({"station_id": "S1", "timestamp": 100.0, "anomaly_score": 0.20})
        p4.ingest_prediction({"station_id": "S1", "timestamp": 500.0, "anomaly_score": 0.99})  # Future

        summary = p4.get_station_summary("S1", as_of_timestamp=200.0)
        self.assertEqual(summary.max_anomaly_score, 0.20)
        self.assertEqual(summary.anomaly_detected_count, 0)

    # 10. Future Phase 5 Zero-Leakage
    def test_10_future_phase5_leakage(self) -> None:
        p5 = Phase5Adapter()
        p5.ingest_snapshot({"timestamp": 100.0, "predicted_bottleneck_station": None, "bottleneck_risk": 0.1})
        p5.ingest_snapshot({"timestamp": 500.0, "predicted_bottleneck_station": "S3", "bottleneck_risk": 0.95})

        exp = p5.get_station_bottleneck_exposure("S3", as_of_timestamp=200.0)
        self.assertEqual(exp["max_bottleneck_risk"], 0.0)

    # 11. Phase 4 Adapter Compatibility
    def test_11_phase4_adapter_compatibility(self) -> None:
        p4 = Phase4Adapter()
        p4.ingest_prediction({
            "station_id": "S3",
            "timestamp": 150.0,
            "anomaly_score": 0.88,
            "severity": "HIGH",
            "detected": True,
            "top_signals": ["vibration", "temperature"],
        })
        preds = p4.get_predictions_as_of(150.0, "S3")
        self.assertEqual(len(preds), 1)
        self.assertEqual(preds[0].severity, "HIGH")

    # 12. Phase 5 Adapter Compatibility
    def test_12_phase5_adapter_compatibility(self) -> None:
        p5 = Phase5Adapter()
        p5.ingest_snapshot(
            BottleneckSnapshot(
                timestamp=150.0,
                predicted_bottleneck_station="S2",
                bottleneck_risk=0.80,
                propagation_risk=0.50,
            )
        )
        snap = p5.get_latest_bottleneck_state(150.0)
        self.assertIsNotNone(snap)
        self.assertEqual(snap.predicted_bottleneck_station, "S2")

    # 13. Preprocessing Consistency
    def test_13_preprocessing_consistency(self) -> None:
        X = np.random.randn(20, len(QUALITY_FEATURE_NAMES)).astype(np.float32)
        prep = VehicleFeaturePreprocessor()
        prep.fit(X)
        transformed = prep.transform(X)
        self.assertEqual(transformed.shape, X.shape)
        # Scaled mean should be close to 0
        self.assertTrue(np.allclose(np.mean(transformed, axis=0), 0.0, atol=1e-5))

    # 14. Logistic Regression Model Fit & Predict
    def test_14_logistic_regression(self) -> None:
        X = np.random.randn(30, 10).astype(np.float32)
        y = np.array([0] * 20 + [1] * 10)
        model = LogisticRegressionQualityModel(random_state=42)
        model.fit(X, y)
        probs = model.predict_proba(X)
        self.assertEqual(len(probs), 30)
        self.assertTrue((probs >= 0.0).all() and (probs <= 1.0).all())

    # 15. Random Forest Model Fit & Predict
    def test_15_random_forest(self) -> None:
        X = np.random.randn(30, 10).astype(np.float32)
        y = np.array([0] * 20 + [1] * 10)
        model = RandomForestQualityModel(n_estimators=10, random_state=42)
        model.fit(X, y)
        probs = model.predict_proba(X)
        self.assertEqual(len(probs), 30)
        self.assertTrue((probs >= 0.0).all() and (probs <= 1.0).all())

    # 16. XGBoost Model Fit & Predict
    def test_16_xgboost(self) -> None:
        X = np.random.randn(30, 10).astype(np.float32)
        y = np.array([0] * 20 + [1] * 10)
        model = XGBoostQualityModel(n_estimators=10, random_state=42)
        model.fit(X, y)
        probs = model.predict_proba(X)
        self.assertEqual(len(probs), 30)
        self.assertTrue((probs >= 0.0).all() and (probs <= 1.0).all())

    # 17. Model Save and Load
    def test_17_model_save_and_load(self) -> None:
        X = np.random.randn(30, 10).astype(np.float32)
        y = np.array([0] * 20 + [1] * 10)
        model = XGBoostQualityModel(n_estimators=10, random_state=42)
        model.fit(X, y)
        save_file = os.path.join(self.test_dir, "test_xgb.json")
        model.save(save_file)

        loaded_model = XGBoostQualityModel().load(save_file)
        orig_probs = model.predict_proba(X)
        loaded_probs = loaded_model.predict_proba(X)
        self.assertTrue(np.allclose(orig_probs, loaded_probs, atol=1e-5))

    # 18. Probability Calibration
    def test_18_probability_calibration(self) -> None:
        X = np.random.randn(40, 5).astype(np.float32)
        y = np.array([0] * 25 + [1] * 15)
        model = XGBoostQualityModel(n_estimators=10, random_state=42).fit(X, y)

        calibrator = QualityProbabilityCalibrator(method="isotonic")
        calibrator.fit(model, X, y)
        calibrated = calibrator.calibrate(model.predict_proba(X))
        self.assertTrue((calibrated >= 0.0).all() and (calibrated <= 1.0).all())

    # 19. Risk Classification & Action Mapping
    def test_19_risk_classification(self) -> None:
        policy = QualityRiskPolicy(low_threshold=0.25, high_threshold=0.60)
        score_low, exp_low, act_low = policy.evaluate_risk(0.10)
        self.assertEqual(exp_low, "LOW")
        self.assertEqual(act_low, "PASS_MONITOR")

        score_med, exp_med, act_med = policy.evaluate_risk(0.40)
        self.assertEqual(exp_med, "MEDIUM")
        self.assertEqual(act_med, "REVIEW_AUDIT")

        score_high, exp_high, act_high = policy.evaluate_risk(0.85)
        self.assertEqual(exp_high, "HIGH")
        self.assertEqual(act_high, "QA_INSPECTION")

    # 20. SHAP Explanation
    def test_20_shap_explanation(self) -> None:
        X = np.random.randn(30, 5).astype(np.float32)
        y = np.array([0] * 20 + [1] * 10)
        names = [f"f_{i}" for i in range(5)]
        model = XGBoostQualityModel(n_estimators=10, random_state=42).fit(X, y)

        explainer = QualityExplainer(model, names)
        factors = explainer.explain_instance(X[0], top_k=3)
        self.assertGreaterEqual(len(factors), 1)
        self.assertIn("feature", factors[0])
        self.assertIn("contribution", factors[0])
        self.assertIn("direction", factors[0])

    # 21. Schema Validation
    def test_21_schema_validation(self) -> None:
        pred = VehicleRiskPrediction(
            vehicle_id="V_TEST",
            timestamp=100.0,
            risk_score=75.0,
            defect_probability=0.75,
            quality_exposure="HIGH",
            recommended_action="QA_INSPECTION",
            top_risk_factors=[],
        )
        d = pred.to_dict()
        self.assertEqual(d["vehicle_id"], "V_TEST")
        self.assertEqual(d["quality_exposure"], "HIGH")

        with self.assertRaises(ValueError):
            # Invalid probability
            VehicleRiskPrediction(
                vehicle_id="V_ERR",
                timestamp=100.0,
                risk_score=50.0,
                defect_probability=1.5,
                quality_exposure="HIGH",
                recommended_action="QA_INSPECTION",
            )

    # 22. Deterministic Inference
    def test_22_deterministic_inference(self) -> None:
        service = QualityRiskService()
        p1 = service.predict("V1", self.normal_history, self.base_time + 400.0)
        p2 = service.predict("V1", self.normal_history, self.base_time + 400.0)
        self.assertEqual(p1.defect_probability, p2.defect_probability)
        self.assertEqual(p1.risk_score, p2.risk_score)
        self.assertEqual(p1.recommended_action, p2.recommended_action)

    # 23. CRITICAL ZERO-LEAKAGE VERIFICATION TEST
    def test_23_critical_zero_leakage(self) -> None:
        """
        Critical Zero-Leakage Test: Modifying or adding events strictly after timestamp `t`
        must NOT alter predictions at timestamp `t`.
        """
        service = QualityRiskService()
        t_as_of = self.base_time + 100.0  # As of step 2 (S2)

        # Baseline prediction at t_as_of
        pred_base = service.predict(
            vehicle_id="V_LEAK_TEST",
            vehicle_history=self.normal_history,
            as_of_timestamp=t_as_of,
            phase4_adapter=self.p4_adapter,
            phase5_adapter=self.p5_adapter,
        )

        # Inject severe future failure at t = t_as_of + 500.0
        future_history = copy.deepcopy(self.normal_history)
        future_history.append(
            VehicleObservation(
                vehicle_id="V_LEAK_TEST",
                station_id="S6",
                timestamp=t_as_of + 500.0,
                vibration=0.99,
                temperature=150.0,
                motor_current=50.0,
                current_variance=2.0,
                machine_state="DOWN",
            )
        )

        # Future Phase 4 event
        future_p4 = copy.deepcopy(self.p4_adapter)
        future_p4.ingest_prediction({
            "station_id": "S6",
            "timestamp": t_as_of + 500.0,
            "anomaly_score": 0.99,
            "severity": "HIGH",
            "detected": True,
        })

        # Future Phase 5 event
        future_p5 = copy.deepcopy(self.p5_adapter)
        future_p5.ingest_snapshot(
            BottleneckSnapshot(
                timestamp=t_as_of + 500.0,
                predicted_bottleneck_station="S6",
                bottleneck_risk=0.99,
            )
        )

        # Generate prediction at t_as_of with future contaminated data
        pred_future = service.predict(
            vehicle_id="V_LEAK_TEST",
            vehicle_history=future_history,
            as_of_timestamp=t_as_of,
            phase4_adapter=future_p4,
            phase5_adapter=future_p5,
        )

        # Verify exact equivalence
        self.assertAlmostEqual(
            pred_base.defect_probability,
            pred_future.defect_probability,
            places=5,
            msg="Defect probability leaked future information!",
        )
        self.assertAlmostEqual(
            pred_base.risk_score,
            pred_future.risk_score,
            places=4,
            msg="Risk score leaked future information!",
        )
        self.assertEqual(pred_base.quality_exposure, pred_future.quality_exposure)
        self.assertEqual(pred_base.recommended_action, pred_future.recommended_action)


if __name__ == "__main__":
    unittest.main()
