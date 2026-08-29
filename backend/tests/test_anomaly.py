"""
Comprehensive test suite for Phase 4 ML Anomaly Detection Subsystem.

Covers the 10 required test suites:
1. Normal telemetry
2. Gradual degradation
3. Sudden failure
4. Sensor missingness
5. Anomaly threshold behavior
6. Preprocessing consistency
7. Prediction output schema
8. Detection lead time
9. Model save/load
10. Deterministic/reproducible behavior
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import numpy as np

from backend.analytics.baseline import calculate_baseline
from backend.app.models.anomaly.features import (
    ANOMALY_FEATURE_NAMES,
    FeatureScaler,
    encode_machine_state,
    extract_station_features,
)
from backend.app.models.anomaly.isolation_forest import IsolationForestAnomalyModel
from backend.app.models.anomaly.lstm_autoencoder import LSTMAutoencoderModel
from backend.app.models.anomaly.service import AnomalyService
from backend.app.schemas.anomaly import AnomalyPrediction, SeverityLevel
from backend.data.synthetic_factory import (
    ScenarioType,
    generate_full_factory_dataset,
    simulate_factory_run,
)


from backend.training.train_anomaly import prepare_tabular_and_sequence_data


class TestAnomalySubsystem(unittest.TestCase):
    """Phase 4 Anomaly Detection Comprehensive Test Suite."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.seed = 42
        cls.window_size = 10
        cls.dataset = generate_full_factory_dataset(
            n_train_runs=4,
            n_val_runs=2,
            steps_per_run=40,
            random_seed=cls.seed,
        )
        cls.baseline = calculate_baseline([s.to_dict() for s in cls.dataset["train"]])

        train_2d, train_3d, cls.scaler = prepare_tabular_and_sequence_data(
            snapshots=cls.dataset["train"],
            window_size=cls.window_size,
            baseline=cls.baseline,
            fit_scaler=True,
        )
        val_2d, val_3d, _ = prepare_tabular_and_sequence_data(
            snapshots=cls.dataset["val"],
            scaler=cls.scaler,
            window_size=cls.window_size,
            baseline=cls.baseline,
            fit_scaler=False,
        )

        # Fit Isolation Forest
        cls.if_model = IsolationForestAnomalyModel(n_estimators=50, random_state=cls.seed)
        cls.if_model.fit(train_2d, val_X=val_2d)

        # Fit LSTM Autoencoder
        cls.lstm_model = LSTMAutoencoderModel(
            window_size=cls.window_size,
            input_dim=11,
            hidden_dim=16,
            num_layers=1,
            epochs=20,
            random_state=cls.seed,
        )
        cls.lstm_model.fit(train_3d, val_X=val_3d)

    # 1. Normal Telemetry Test
    def test_01_normal_telemetry(self) -> None:
        """Nominal operational telemetry should produce low anomaly scores and no alarms."""
        normal_snaps = simulate_factory_run(
            run_id="test_normal",
            scenario=ScenarioType.NORMAL,
            total_steps=20,
            random_seed=123,
        )
        service = AnomalyService(model=self.lstm_model, scaler=self.scaler, baseline=self.baseline)
        for snap in normal_snaps:
            batch = service.predict_factory_snapshot(snap.to_dict())
            for st_id, pred in batch.predictions.items():
                self.assertLess(pred.anomaly_score, 0.70, f"False alarm on normal station {st_id}")

    # 2. Gradual Degradation Test
    def test_02_gradual_degradation(self) -> None:
        """Station S3 bearing degradation should be detected before final bottleneck."""
        degraded_snaps = simulate_factory_run(
            run_id="test_deg",
            scenario=ScenarioType.GRADUAL_S3_DEGRADATION,
            total_steps=50,
            random_seed=456,
        )
        service = AnomalyService(model=self.lstm_model, scaler=self.scaler, baseline=self.baseline)
        detected_at_step = None
        for step_idx, snap in enumerate(degraded_snaps):
            batch = service.predict_factory_snapshot(
                snap.to_dict(),
                ground_truth_events=snap.ground_truth_failure_times,
            )
            s3_pred = batch.predictions["S3"]
            if s3_pred.detected and detected_at_step is None:
                detected_at_step = step_idx

        self.assertIsNotNone(detected_at_step, "Gradual S3 degradation was never detected")
        self.assertLess(detected_at_step, 45, "Anomaly must be detected BEFORE the bottleneck at step 45")

    # 3. Sudden Machine Failure Test
    def test_03_sudden_failure(self) -> None:
        """Sudden machine breakdown on S2 should trigger immediate high anomaly score."""
        failure_snaps = simulate_factory_run(
            run_id="test_sudden",
            scenario=ScenarioType.SUDDEN_FAILURE,
            total_steps=35,
            random_seed=789,
        )
        service = AnomalyService(model=self.if_model, scaler=self.scaler, baseline=self.baseline)
        breakdown_pred = None
        for snap in failure_snaps:
            batch = service.predict_factory_snapshot(snap.to_dict())
            if snap.step_index >= 26:
                s2_pred = batch.predictions["S2"]
                if s2_pred.detected:
                    breakdown_pred = s2_pred

        self.assertIsNotNone(breakdown_pred, "Sudden machine breakdown on S2 was not detected")
        self.assertIn("DOWN", failure_snaps[-1].stations["S2"]["machine_state"])

    # 4. Sensor Missingness Test
    def test_04_sensor_missingness(self) -> None:
        """Telemetry with missing/null sensor channels should be gracefully imputed without crashing."""
        missing_snaps = simulate_factory_run(
            run_id="test_missing",
            scenario=ScenarioType.SENSOR_MISSINGNESS,
            total_steps=15,
            random_seed=999,
        )
        service = AnomalyService(model=self.lstm_model, scaler=self.scaler, baseline=self.baseline)
        for snap in missing_snaps:
            batch = service.predict_factory_snapshot(snap.to_dict())
            self.assertEqual(len(batch.predictions), 6)
            for st_id, pred in batch.predictions.items():
                self.assertIsInstance(pred.anomaly_score, float)
                self.assertFalse(np.isnan(pred.anomaly_score))

    # 5. Anomaly Threshold Behavior Test
    def test_05_threshold_behavior(self) -> None:
        """Statistical thresholding should correctly flag deviations."""
        self.assertGreater(self.lstm_model.threshold, 0.0)
        self.assertGreater(self.if_model.threshold, 0.0)
        # Test synthetic high anomaly input
        fake_anomalous_seq = np.ones((1, 10, 11), dtype=np.float32) * 10.0
        is_anom = self.lstm_model.predict(fake_anomalous_seq)[0]
        self.assertTrue(is_anom)

    # 6. Preprocessing Consistency Test
    def test_06_preprocessing_consistency(self) -> None:
        """Feature scaler must invert transformed values accurately."""
        sample_feats = np.array([[54.0, 0.0, 0.88, 2.0, 2.0, 65.0, 0.10, 5.2, 0.05, 3.0, 0.0]], dtype=np.float32)
        scaled = self.scaler.transform(sample_feats)
        reconstructed = self.scaler.inverse_transform(scaled)
        np.testing.assert_allclose(sample_feats, reconstructed, rtol=1e-4)

    # 7. Prediction Output Schema Test
    def test_07_prediction_output_schema(self) -> None:
        """AnomalyPrediction must contain all contract fields and valid types."""
        service = AnomalyService(model=self.if_model, scaler=self.scaler, baseline=self.baseline)
        pred = service.predict_station(
            station_id="S1",
            station_telemetry={"cycle_time": 45.0, "state": "RUNNING"},
            timestamp=1700000000.0,
        )
        self.assertIsInstance(pred, AnomalyPrediction)
        self.assertEqual(pred.station_id, "S1")
        self.assertEqual(pred.timestamp, 1700000000.0)
        self.assertIsInstance(pred.anomaly_score, float)
        self.assertIn(pred.severity, [s.value for s in SeverityLevel])
        self.assertIsInstance(pred.detected, bool)
        self.assertIsInstance(pred.top_signals, list)

    # 8. Detection Lead Time Test
    def test_08_detection_lead_time(self) -> None:
        """Lead time must be positive when anomaly is detected before the ground-truth bottleneck."""
        service = AnomalyService(model=self.if_model, scaler=self.scaler, baseline=self.baseline)
        # Step 1: Detect anomaly at t=100
        pred1 = service.predict_station(
            station_id="S3",
            station_telemetry={"cycle_time": 90.0, "vibration": 0.8, "state": "FAULT"},
            timestamp=100.0,
            ground_truth_failure_time=250.0,
        )
        self.assertTrue(pred1.detected)
        self.assertEqual(pred1.lead_time_if_known, 150.0)

    # 9. Model Save and Load Test
    def test_09_model_save_and_load(self) -> None:
        """Saved models must restore identically and yield equivalent predictions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.if_model.save(tmpdir)
            self.lstm_model.save(tmpdir)
            self.scaler.save(os.path.join(tmpdir, "scaler.json"))

            loaded_if = IsolationForestAnomalyModel.load(tmpdir)
            loaded_lstm = LSTMAutoencoderModel.load(tmpdir)
            loaded_scaler = FeatureScaler.load(os.path.join(tmpdir, "scaler.json"))

            # Test equivalence
            test_x2d = np.zeros((2, 11), dtype=np.float32)
            np.testing.assert_allclose(
                self.if_model.score_samples(test_x2d),
                loaded_if.score_samples(test_x2d),
            )

            test_x3d = np.zeros((2, 10, 11), dtype=np.float32)
            np.testing.assert_allclose(
                self.lstm_model.score_samples(test_x3d),
                loaded_lstm.score_samples(test_x3d),
                atol=1e-5,
            )

    # 10. Determinism and Reproducibility Test
    def test_10_deterministic_behavior(self) -> None:
        """Identical inputs with fixed seed must generate identical model predictions."""
        test_seq = np.random.RandomState(42).randn(3, 10, 11).astype(np.float32)
        score1 = self.lstm_model.score_samples(test_seq)
        score2 = self.lstm_model.score_samples(test_seq)
        np.testing.assert_array_equal(score1, score2)


if __name__ == "__main__":
    unittest.main()
