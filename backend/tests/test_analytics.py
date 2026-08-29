"""
Comprehensive unit and integration test suite for backend.analytics package.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from backend.analytics.baseline import (
    DEFAULT_METRICS,
    DEFAULT_STATIONS,
    FactoryBaseline,
    MetricBaseline,
    StationBaseline,
    calculate_baseline,
    load_baseline,
    save_baseline,
)
from backend.analytics.buffer import (
    BufferAnalytics,
    BufferPressureLevel,
    BufferTracker,
    StationFlowAnalytics,
    calculate_blocking,
    calculate_buffer_pressure,
    calculate_starvation,
    get_pressure_level,
)
from backend.analytics.confidence import (
    SensorConfidenceResult,
    calculate_data_freshness,
    calculate_sensor_confidence,
)
from backend.analytics.cusum import (
    CUSUMDetector,
    CUSUMDirection,
    StationCUSUMTracker,
)
from backend.analytics.deviation import (
    calculate_delta,
    calculate_deviation_score,
    calculate_z_score,
    normalize_z_to_deviation,
)
from backend.analytics.ewma import (
    EWMADetector,
    StationEWMATracker,
)
from backend.analytics.health import (
    HealthLevel,
    calculate_factory_health,
    calculate_station_health,
    score_to_health_level,
)
from backend.analytics.pipeline import (
    AnalyticsEngine,
    AnalyticsPipelineConfig,
    FactoryAnalytics,
    analyze_factory,
)


class TestBaselineModule(unittest.TestCase):
    """Unit tests for baseline calculation and persistence."""

    def setUp(self) -> None:
        self.sample_snapshots = [
            {
                "stations": {
                    "S1": {
                        "cycle_time": 10.0,
                        "utilization": 0.80,
                        "queue": 1,
                        "WIP": 2,
                        "temperature": 65.0,
                        "vibration": 0.10,
                        "motor_current": 5.0,
                        "current_variance": 0.05,
                    },
                    "S2": {
                        "cycle_time": 12.0,
                        "utilization": 0.85,
                        "queue": 2,
                        "WIP": 3,
                        "temperature": 70.0,
                        "vibration": 0.15,
                        "motor_current": 6.0,
                        "current_variance": 0.08,
                    },
                }
            },
            {
                "stations": {
                    "S1": {
                        "cycle_time": 12.0,
                        "utilization": 0.82,
                        "queue": 2,
                        "WIP": 2,
                        "temperature": 67.0,
                        "vibration": 0.12,
                        "motor_current": 5.2,
                        "current_variance": 0.06,
                    },
                    "S2": {
                        "cycle_time": 14.0,
                        "utilization": 0.87,
                        "queue": 3,
                        "WIP": 4,
                        "temperature": 72.0,
                        "vibration": 0.17,
                        "motor_current": 6.4,
                        "current_variance": 0.10,
                    },
                }
            },
            {
                "stations": {
                    "S1": {
                        "cycle_time": 11.0,
                        "utilization": 0.81,
                        "queue": 1,
                        "WIP": 2,
                        "temperature": 66.0,
                        "vibration": 0.11,
                        "motor_current": 5.1,
                        "current_variance": 0.055,
                    },
                    "S2": {
                        "cycle_time": 13.0,
                        "utilization": 0.86,
                        "queue": 2,
                        "WIP": 3,
                        "temperature": 71.0,
                        "vibration": 0.16,
                        "motor_current": 6.2,
                        "current_variance": 0.09,
                    },
                }
            },
        ]

    def test_calculate_baseline_means_and_std(self) -> None:
        baseline = calculate_baseline(self.sample_snapshots)
        self.assertIsInstance(baseline, FactoryBaseline)
        self.assertIn("S1", baseline.stations)
        self.assertIn("S2", baseline.stations)

        s1_cycle = baseline.stations["S1"].get_metric("cycle_time")
        self.assertIsNotNone(s1_cycle)
        self.assertAlmostEqual(s1_cycle.mean, 11.0, places=2)
        self.assertAlmostEqual(s1_cycle.std, 1.0, places=2)
        self.assertEqual(s1_cycle.count, 3)
        self.assertEqual(s1_cycle.min_val, 10.0)
        self.assertEqual(s1_cycle.max_val, 12.0)

    def test_calculate_baseline_dict_format(self) -> None:
        dict_data = {
            "S3": [
                {"temperature": 60.0, "vibration": 0.05},
                {"temperature": 64.0, "vibration": 0.07},
            ]
        }
        baseline = calculate_baseline(dict_data)
        self.assertIn("S3", baseline.stations)
        s3_temp = baseline.stations["S3"].get_metric("temperature")
        self.assertIsNotNone(s3_temp)
        self.assertAlmostEqual(s3_temp.mean, 62.0)

    def test_save_and_load_baseline(self) -> None:
        baseline = calculate_baseline(self.sample_snapshots)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            save_baseline(baseline, temp_path)
            loaded = load_baseline(temp_path)
            self.assertEqual(len(loaded.stations), len(baseline.stations))
            self.assertAlmostEqual(
                loaded.stations["S1"].metrics["cycle_time"].mean,
                baseline.stations["S1"].metrics["cycle_time"].mean,
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestDeviationModule(unittest.TestCase):
    """Unit tests for delta, z-score, and deviation score calculation."""

    def test_calculate_delta(self) -> None:
        self.assertEqual(calculate_delta(15.0, 10.0), 5.0)
        self.assertEqual(calculate_delta(8.0, 10.0), -2.0)
        self.assertEqual(calculate_delta(None, 10.0), 0.0)

    def test_calculate_z_score(self) -> None:
        self.assertAlmostEqual(calculate_z_score(15.0, 10.0, 2.5), 2.0)
        self.assertAlmostEqual(calculate_z_score(5.0, 10.0, 2.5), -2.0)
        # Test zero std protection
        z_safe = calculate_z_score(15.0, 10.0, 0.0)
        self.assertGreater(abs(z_safe), 0)

    def test_normalize_z_to_deviation(self) -> None:
        d0 = normalize_z_to_deviation(0.0)
        d1 = normalize_z_to_deviation(1.0)
        d3 = normalize_z_to_deviation(3.0)
        d10 = normalize_z_to_deviation(10.0)

        self.assertEqual(d0, 0.0)
        self.assertGreater(d1, d0)
        self.assertGreater(d3, d1)
        self.assertAlmostEqual(d10, 1.0, places=2)

    def test_calculate_deviation_score(self) -> None:
        st_base = StationBaseline(
            station_id="S1",
            metrics={
                "temperature": MetricBaseline("temperature", 70.0, 2.0, 66.0, 74.0, 20, 73.0),
                "vibration": MetricBaseline("vibration", 0.10, 0.02, 0.06, 0.14, 20, 0.13),
            },
        )
        observed = {"temperature": 76.0, "vibration": 0.16}  # +3 sigma each
        dev_res = calculate_deviation_score(observed, st_base)

        self.assertEqual(dev_res.station_id, "S1")
        self.assertGreater(dev_res.composite_deviation, 0.5)
        self.assertIn("temperature", dev_res.anomalous_metrics)
        self.assertIn("vibration", dev_res.anomalous_metrics)
        self.assertEqual(len(dev_res.metric_deviations), 2)


class TestEWMAModule(unittest.TestCase):
    """Unit tests for EWMA drift detection."""

    def test_ewma_smoothing_and_alarm(self) -> None:
        detector = EWMADetector(alpha=0.2, target_mean=50.0, std=2.0, threshold=3.0)

        # Baseline observations
        res1 = detector.update(50.0)
        self.assertEqual(res1.current_ewma, 50.0)
        self.assertFalse(res1.threshold_crossed)

        # Introduce small noise
        res2 = detector.update(51.0)
        self.assertFalse(res2.threshold_crossed)

        # Introduce massive persistent shift
        for _ in range(10):
            res_shift = detector.update(70.0)

        self.assertTrue(res_shift.threshold_crossed)
        self.assertGreater(res_shift.current_ewma, 65.0)

    def test_station_ewma_tracker(self) -> None:
        tracker = StationEWMATracker("S1", alpha=0.3)
        res = tracker.update_station({"temperature": 60.0, "vibration": 0.1})
        self.assertIn("temperature", res)
        self.assertIn("vibration", res)
        self.assertEqual(res["temperature"].current_ewma, 60.0)


class TestCUSUMModule(unittest.TestCase):
    """Unit tests for CUSUM shift detection."""

    def test_cusum_noise_resilience_and_shift(self) -> None:
        detector = CUSUMDetector(target_mean=10.0, drift=0.5, threshold=4.0)

        # Random alternating small noise around mean 10.0
        for val in [10.2, 9.8, 10.3, 9.7, 10.1]:
            res = detector.update(val)
            self.assertFalse(res.detected_change)
            self.assertEqual(res.direction, CUSUMDirection.NONE.value)

        # Persistent upward shift to 14.0
        alarm_triggered = False
        for _ in range(6):
            res = detector.update(14.0)
            if res.detected_change:
                alarm_triggered = True
                self.assertEqual(res.direction, CUSUMDirection.POSITIVE.value)

        self.assertTrue(alarm_triggered)

    def test_cusum_negative_shift(self) -> None:
        detector = CUSUMDetector(target_mean=100.0, drift=2.0, threshold=10.0)
        for _ in range(5):
            res = detector.update(70.0)  # Major downward shift

        self.assertTrue(res.detected_change)
        self.assertEqual(res.direction, CUSUMDirection.NEGATIVE.value)


class TestBufferModule(unittest.TestCase):
    """Unit tests for buffer pressure, blocking, and starvation."""

    def test_calculate_buffer_pressure(self) -> None:
        self.assertAlmostEqual(calculate_buffer_pressure(5, 10), 0.5)
        self.assertAlmostEqual(calculate_buffer_pressure(9.5, 10), 0.95)
        self.assertEqual(calculate_buffer_pressure(0, 10), 0.0)
        self.assertEqual(calculate_buffer_pressure(5, 0), 0.0)  # Zero capacity safety

    def test_pressure_level(self) -> None:
        self.assertEqual(get_pressure_level(0.2), BufferPressureLevel.LOW)
        self.assertEqual(get_pressure_level(0.5), BufferPressureLevel.NORMAL)
        self.assertEqual(get_pressure_level(0.8), BufferPressureLevel.HIGH)
        self.assertEqual(get_pressure_level(0.95), BufferPressureLevel.CRITICAL)

    def test_blocking_and_starvation(self) -> None:
        self.assertAlmostEqual(calculate_blocking(15.0, 60.0), 0.25)
        self.assertAlmostEqual(calculate_starvation(30.0, 60.0), 0.50)
        self.assertEqual(calculate_blocking(70.0, 60.0), 1.0)  # Clamped to 1.0

    def test_buffer_tracker_saturation(self) -> None:
        tracker = BufferTracker("B1", capacity=10.0, saturation_threshold=0.85)

        # Low occupancy
        s1 = tracker.update(3.0)
        self.assertFalse(s1.is_saturated)
        self.assertEqual(s1.saturation_events, 0)

        # Saturated occupancy
        s2 = tracker.update(9.0, time_step_duration=2.0)
        self.assertTrue(s2.is_saturated)
        self.assertEqual(s2.saturation_events, 1)
        self.assertEqual(s2.time_near_saturation, 2.0)


class TestConfidenceModule(unittest.TestCase):
    """Unit tests for sensor confidence evaluation."""

    def test_calculate_data_freshness(self) -> None:
        self.assertEqual(calculate_data_freshness(5.0, max_acceptable_staleness=10.0), 1.0)
        self.assertAlmostEqual(calculate_data_freshness(15.0, max_acceptable_staleness=10.0), 0.5)
        self.assertEqual(calculate_data_freshness(25.0, max_acceptable_staleness=10.0), 0.0)

    def test_calculate_sensor_confidence(self) -> None:
        expected = ["temp", "vib", "curr", "cycle"]
        reporting = {"temp": 70.0, "vib": 0.1, "curr": 5.0, "cycle": 10.0}

        conf_perfect = calculate_sensor_confidence(
            expected_sensors=expected,
            reporting_telemetry=reporting,
            data_age_seconds=1.0,
        )
        self.assertEqual(conf_perfect.coverage, 1.0)
        self.assertEqual(conf_perfect.missing_rate, 0.0)
        self.assertEqual(conf_perfect.data_freshness, 1.0)
        self.assertAlmostEqual(conf_perfect.sensor_confidence, 1.0, places=2)

        # Drop 2 sensors
        reporting_partial = {"temp": 70.0, "vib": 0.1}
        conf_partial = calculate_sensor_confidence(
            expected_sensors=expected,
            reporting_telemetry=reporting_partial,
            data_age_seconds=1.0,
        )
        self.assertEqual(conf_partial.coverage, 0.5)
        self.assertEqual(conf_partial.missing_rate, 0.5)
        self.assertLess(conf_partial.sensor_confidence, 0.8)


class TestHealthModule(unittest.TestCase):
    """Unit tests for station and factory health calculation."""

    def test_station_health_nominal(self) -> None:
        health = calculate_station_health(
            station_id="S1",
            deviation_score=0.0,
            buffer_pressure=0.2,
            blocking_rate=0.0,
            starvation_rate=0.0,
            machine_state="RUNNING",
            telemetry_confidence=1.0,
        )
        self.assertGreaterEqual(health.health_score, 85.0)
        self.assertEqual(health.health_level, HealthLevel.NOMINAL.value)
        self.assertTrue(health.is_healthy)

    def test_station_health_fault(self) -> None:
        health = calculate_station_health(
            station_id="S2",
            deviation_score=0.9,
            buffer_pressure=0.95,
            blocking_rate=0.8,
            starvation_rate=0.0,
            machine_state="FAULT",
            telemetry_confidence=0.5,
        )
        self.assertLess(health.health_score, 45.0)
        self.assertEqual(health.health_level, HealthLevel.CRITICAL.value)
        self.assertFalse(health.is_healthy)

    def test_factory_health_aggregation(self) -> None:
        s1 = calculate_station_health("S1", deviation_score=0.0, machine_state="RUNNING")
        s2 = calculate_station_health("S2", deviation_score=0.8, machine_state="FAULT")
        s3 = calculate_station_health("S3", deviation_score=0.1, machine_state="RUNNING")

        factory_health = calculate_factory_health(
            station_healths=[s1, s2, s3],
            buffer_pressures={"B1": 0.3, "B2": 0.85},
        )
        self.assertIn("S2", factory_health.critical_stations)
        self.assertEqual(factory_health.bottleneck_station, "S2")
        self.assertGreater(len(factory_health.active_alarms), 0)


class TestPipelineIntegration(unittest.TestCase):
    """Integration tests for the complete 12-step analyze_factory pipeline."""

    def setUp(self) -> None:
        # Pre-generate 10 timesteps of normal telemetry for baseline
        self.history = []
        for i in range(10):
            snap = {
                "timestamp": 1700000000.0 + i * 5,
                "stations": {
                    f"S{k}": {
                        "cycle_time": 10.0 + (k * 0.5),
                        "utilization": 0.85,
                        "queue": 1,
                        "WIP": 2,
                        "temperature": 65.0 + (k * 2.0),
                        "vibration": 0.10,
                        "motor_current": 5.0,
                        "current_variance": 0.05,
                        "state": "RUNNING",
                        "blocked_time": 0.0,
                        "starved_time": 0.0,
                    }
                    for k in range(1, 7)
                },
                "buffers": {
                    f"B{k}": {"occupancy": 3.0, "capacity": 10.0, "upstream": f"S{k}", "downstream": f"S{k+1}"}
                    for k in range(1, 6)
                },
            }
            self.history.append(snap)

    def test_analyze_factory_end_to_end(self) -> None:
        current_state = {
            "timestamp": 1700000100.0,
            "stations": {
                "S1": {
                    "cycle_time": 10.2,
                    "utilization": 0.86,
                    "queue": 1,
                    "WIP": 2,
                    "temperature": 66.0,
                    "vibration": 0.11,
                    "motor_current": 5.1,
                    "current_variance": 0.05,
                    "state": "RUNNING",
                    "blocked_time": 0.0,
                    "starved_time": 0.0,
                },
                "S2": {
                    # Severe anomaly on S2
                    "cycle_time": 25.0,
                    "utilization": 0.30,
                    "queue": 8,
                    "WIP": 10,
                    "temperature": 95.0,
                    "vibration": 0.45,
                    "motor_current": 12.0,
                    "current_variance": 0.50,
                    "state": "FAULT",
                    "blocked_time": 20.0,
                    "starved_time": 0.0,
                },
                "S3": {
                    "cycle_time": 11.5,
                    "utilization": 0.85,
                    "queue": 1,
                    "WIP": 2,
                    "temperature": 70.0,
                    "vibration": 0.10,
                    "motor_current": 5.0,
                    "current_variance": 0.05,
                    "state": "RUNNING",
                    "blocked_time": 0.0,
                    "starved_time": 15.0,
                },
            },
            "buffers": {
                "B1": {"occupancy": 9.5, "capacity": 10.0, "upstream": "S1", "downstream": "S2"},
                "B2": {"occupancy": 1.0, "capacity": 10.0, "upstream": "S2", "downstream": "S3"},
            },
            "observation_window": 60.0,
        }

        analytics = analyze_factory(
            factory_state=current_state,
            telemetry_history=self.history,
        )

        self.assertIsInstance(analytics, FactoryAnalytics)
        self.assertIsNotNone(analytics.factory_health)
        self.assertEqual(analytics.highest_deviation_station, "S2")
        self.assertEqual(analytics.highest_buffer_pressure, "B1")
        self.assertEqual(analytics.highest_blocking_risk, "S2")
        self.assertEqual(analytics.highest_starvation_risk, "S3")

        # Check serialization
        analytics_dict = analytics.to_dict()
        self.assertIn("factory_health", analytics_dict)
        self.assertIn("stations", analytics_dict)
        self.assertIn("buffers", analytics_dict)

        # JSON encodable
        json_str = json.dumps(analytics_dict)
        self.assertIsInstance(json_str, str)
        self.assertGreater(len(json_str), 100)

    def test_stateful_analytics_engine(self) -> None:
        engine = AnalyticsEngine()
        baseline = calculate_baseline(self.history)
        engine.set_baseline(baseline)

        # Feed 3 successive steps
        for step in range(3):
            state = {
                "timestamp": 1700000200.0 + step * 2,
                "stations": {
                    "S1": {
                        "cycle_time": 10.0 + step * 0.1,
                        "temperature": 65.0 + step * 0.2,
                        "vibration": 0.10,
                        "motor_current": 5.0,
                        "state": "RUNNING",
                    }
                },
                "buffers": {"B1": {"occupancy": 4.0, "capacity": 10.0}},
            }
            res = engine.analyze(state)
            self.assertEqual(len(res.stations), 1)
            s1_analytics = res.stations[0]
            self.assertEqual(s1_analytics.station_id, "S1")
            self.assertIn("temperature", s1_analytics.ewma)
            self.assertIn("temperature", s1_analytics.cusum)
            self.assertEqual(s1_analytics.ewma["temperature"].step_count, step + 1)


if __name__ == "__main__":
    unittest.main()
