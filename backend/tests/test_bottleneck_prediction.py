import pytest

from backend.bottleneck.models import (
    AnomalyPrediction,
    BottleneckClass,
    BottleneckEvidence,
    StationBottleneckRisk,
)
from backend.bottleneck.risk import BottleneckRiskEngine
from backend.bottleneck.persistence import TemporalPersistenceTracker
from backend.bottleneck.propagation import SpatialPropagationAnalyzer
from backend.bottleneck.ranking import StationRanker
from backend.bottleneck.pipeline import (
    BottleneckPipeline,
    Phase4AnomalyProvider,
)
from backend.models.enums import StationId, BufferId


def telemetry(**overrides):
    data = {
        "machine_state": "RUNNING",
        "cycle_time": 54.0,
        "baseline_cycle_time": 54.0,
        "cycle_time_deviation": 0.0,
        "cycle_time_trend": 0.0,
        "queue_length": 0,
        "queue_growth_rate": 0.0,
        "buffer_occupancy": 0,
        "buffer_capacity": 5,
        "buffer_pressure": 0.0,
        "arrival_rate": 1.0,
        "departure_rate": 1.0,
        "arrival_departure_imbalance": 0.0,
        "sensor_missing_flag": False,
        "instrumentation_level": "HIGH",
    }
    data.update(overrides)
    return data


def phase4_prediction(
    station=StationId.S3,
    score=0.82,
    detected=True,
    probability=None,
):
    return AnomalyPrediction(
        station_id=station,
        timestamp=100.0,
        anomaly_score=score,
        anomaly_probability=probability,
        severity="HIGH",
        detected=detected,
        lead_time_if_known=None,
        top_signals=["cycle_time", "vibration"],
    )


class FakePhase4Provider(Phase4AnomalyProvider):
    def __init__(self, prediction):
        self.prediction = prediction

    def get_anomaly_prediction(self, station_id, timestamp, telemetry):
        return self.prediction


def test_normal_telemetry_has_low_bottleneck_risk():
    engine = BottleneckRiskEngine()

    risk, confidence, evidence, components = engine.compute_station_risk(
        telemetry()
    )

    assert 0.0 <= risk <= 1.0
    assert risk < 0.35
    assert 0.0 <= confidence <= 1.0
    assert isinstance(evidence, list)
    assert "cycle_time_pressure" in components


def test_cycle_time_degradation_increases_risk():
    engine = BottleneckRiskEngine()

    risk, _, evidence, components = engine.compute_station_risk(
        telemetry(
            cycle_time=70.0,
            cycle_time_deviation=0.25,
            cycle_time_trend=1.0,
        )
    )

    assert risk > 0.0
    assert components["cycle_time_pressure"] > 0.0
    assert any(e.signal == "cycle_time_deviation" for e in evidence)


def test_queue_growth_increases_risk():
    engine = BottleneckRiskEngine()

    risk, _, evidence, components = engine.compute_station_risk(
        telemetry(
            queue_length=4,
            queue_growth_rate=0.8,
        )
    )

    assert components["queue_pressure"] > 0.0
    assert risk > 0.0
    assert any(e.signal == "queue_length" for e in evidence)


def test_buffer_pressure_increases_risk():
    engine = BottleneckRiskEngine()

    risk, _, evidence, components = engine.compute_station_risk(
        telemetry(
            buffer_occupancy=5,
            buffer_pressure=1.0,
        )
    )

    assert components["buffer_pressure"] == 1.0
    assert risk > 0.0
    assert any(e.signal == "buffer_occupancy" for e in evidence)


def test_machine_down_produces_high_risk():
    engine = BottleneckRiskEngine()

    risk, confidence, evidence, components = engine.compute_station_risk(
        telemetry(machine_state="DOWN")
    )

    assert risk >= 0.65
    assert components["machine_state_score"] == 1.0
    assert confidence > 0.0
    assert any(e.signal == "machine_state" for e in evidence)


def test_phase4_anomaly_is_consumed():
    engine = BottleneckRiskEngine()
    anomaly = phase4_prediction(score=0.82)

    risk, _, evidence, components = engine.compute_station_risk(
        telemetry(),
        anomaly,
    )

    assert components["anomaly_score"] == pytest.approx(0.82)
    assert risk > 0.0
    assert any(e.source == "ANOMALY" for e in evidence)


def test_phase4_probability_is_not_fabricated():
    engine = BottleneckRiskEngine()

    anomaly = phase4_prediction(
        score=0.82,
        probability=None,
    )

    _, _, _, components = engine.compute_station_risk(
        telemetry(),
        anomaly,
    )

    # Phase 5 may use the score as an anomaly signal,
    # but the original probability remains unavailable.
    assert anomaly.anomaly_probability is None
    assert components["anomaly_score"] == pytest.approx(0.82)


def test_temporal_persistence_damps_initial_spike():
    tracker = TemporalPersistenceTracker()

    persistence = tracker.update_and_evaluate(
        StationId.S3,
        timestamp=0.0,
        instantaneous_risk=0.50,
    )

    assert 0.0 <= persistence <= 1.0
    assert persistence < 0.50


def test_temporal_persistence_increases_with_sustained_risk():
    tracker = TemporalPersistenceTracker()

    scores = []

    for i in range(6):
        scores.append(
            tracker.update_and_evaluate(
                StationId.S3,
                timestamp=float(i * 30),
                instantaneous_risk=0.60,
            )
        )

    assert scores[-1] > scores[0]
    assert scores[-1] > 0.60


def test_critical_risk_bypasses_temporal_damping():
    tracker = TemporalPersistenceTracker()

    tracker.update_and_evaluate(
        StationId.S3,
        timestamp=0.0,
        instantaneous_risk=0.60,
    )

    effective = tracker.get_smoothed_risk(
        StationId.S3,
        instantaneous_risk=0.70,
        persistence_score=0.0,
    )

    assert effective == pytest.approx(0.70)


def test_spatial_propagation_for_s3():
    analyzer = SpatialPropagationAnalyzer()

    result = analyzer.analyze_station_propagation(
        station_id=StationId.S3,
        station_risk=0.80,
        buffer_occupancies={
            BufferId.B23: 5,
            BufferId.B34: 0,
        },
    )

    upstream, downstream, propagation, affected, direction = result

    assert upstream > 0.0
    assert downstream > 0.0
    assert propagation == max(upstream, downstream)
    assert StationId.S2 in affected
    assert StationId.S4 in affected


def test_s1_has_no_upstream_station():
    analyzer = SpatialPropagationAnalyzer()

    upstream, downstream, _, affected, _ = (
        analyzer.analyze_station_propagation(
            StationId.S1,
            0.80,
            {BufferId.B12: 0},
        )
    )

    assert upstream == 0.0
    assert downstream > 0.0
    assert StationId.S2 in affected


def test_s6_has_no_downstream_station():
    analyzer = SpatialPropagationAnalyzer()

    upstream, downstream, _, affected, _ = (
        analyzer.analyze_station_propagation(
            StationId.S6,
            0.80,
            {BufferId.B56: 5},
        )
    )

    assert upstream > 0.0
    assert downstream == 0.0
    assert StationId.S5 in affected


def make_station_risk(station_id, score):
    return StationBottleneckRisk(
        station_id=station_id,
        timestamp=0.0,
        risk_score=score,
        prediction=BottleneckClass.NOMINAL,
        confidence=0.9,
    )


def test_station_ranking_orders_highest_first():
    risks = [
        make_station_risk(StationId.S1, 0.20),
        make_station_risk(StationId.S2, 0.60),
        make_station_risk(StationId.S3, 0.85),
        make_station_risk(StationId.S4, 0.30),
        make_station_risk(StationId.S5, 0.45),
        make_station_risk(StationId.S6, 0.10),
    ]

    ranked = StationRanker.rank_stations(risks)

    assert ranked[0].station_id == StationId.S3
    assert ranked[0].risk_score == 0.85
    assert ranked[0].prediction == BottleneckClass.CRITICAL


def test_primary_bottleneck_threshold():
    risks = [
        make_station_risk(StationId.S1, 0.20),
        make_station_risk(StationId.S2, 0.70),
    ]

    ranked = StationRanker.rank_stations(risks)
    primary = StationRanker.get_primary_bottleneck(ranked)

    assert primary is not None
    assert primary.station_id == StationId.S2


def test_bottleneck_dominance():
    risks = [
        make_station_risk(StationId.S1, 0.80),
        make_station_risk(StationId.S2, 0.50),
    ]

    ranked = StationRanker.rank_stations(risks)

    dominance = StationRanker.compute_bottleneck_dominance(ranked)

    assert dominance == pytest.approx(0.30)


def test_phase4_provider_interface():
    prediction = phase4_prediction()

    provider = FakePhase4Provider(prediction)

    result = provider.get_anomaly_prediction(
        StationId.S3,
        100.0,
        telemetry(),
    )

    assert result is prediction
    assert result.station_id == StationId.S3
    assert result.anomaly_score == pytest.approx(0.82)
    assert result.anomaly_probability is None
    assert result.detected is True
    assert result.top_signals == ["cycle_time", "vibration"]


def test_pipeline_accepts_phase4_provider():
    provider = FakePhase4Provider(phase4_prediction())

    pipeline = BottleneckPipeline(
        anomaly_provider=provider,
    )

    result = pipeline.analyze_snapshot(
        timestamp=100.0,
        station_telemetries={
            StationId.S3: telemetry(),
        },
        buffer_occupancies={},
    )

    assert result is not None

    # Phase 5 produces a factory-wide S1-S6 ranking.
    assert len(result.station_ranking) == 6

    # The Phase 4 anomaly provider is consumed by the pipeline.
    s3 = next(
        station
        for station in result.station_ranking
        if station.station_id == StationId.S3
    )

    assert s3.anomaly_score == pytest.approx(0.82)
    assert s3.anomaly_probability is None
    assert s3.anomaly_detected is True
def test_pipeline_does_not_require_phase4_probability():
    provider = FakePhase4Provider(
        phase4_prediction(
            score=0.82,
            probability=None,
        )
    )

    pipeline = BottleneckPipeline(
        anomaly_provider=provider,
    )

    result = pipeline.analyze_snapshot(
        timestamp=100.0,
        station_telemetries={
            StationId.S3: telemetry(),
        },
        buffer_occupancies={},
    )

    station = result.station_ranking[0]

    assert station.anomaly_score == pytest.approx(0.82)
    assert station.anomaly_probability is None


def test_risk_components_are_bounded():
    engine = BottleneckRiskEngine()

    risk, confidence, _, components = engine.compute_station_risk(
        telemetry(
            cycle_time_deviation=1.0,
            cycle_time_trend=10.0,
            queue_length=10,
            queue_growth_rate=10.0,
            buffer_occupancy=5,
            buffer_pressure=1.0,
            arrival_departure_imbalance=10.0,
            machine_state="DOWN",
        ),
        phase4_prediction(score=1.0),
    )

    assert 0.0 <= risk <= 1.0
    assert 0.0 <= confidence <= 1.0

    for value in components.values():
        assert 0.0 <= value <= 1.0