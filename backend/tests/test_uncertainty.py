import pytest
from backend.app.analytics.uncertainty import generate_monte_carlo_uncertainty_passes

def test_monte_carlo_uncertainty_passes_nominal():
    res = generate_monte_carlo_uncertainty_passes(
        station_id="S1",
        baseline_cycle_time=52.0,
        current_cycle_time=53.0,
        current_variance=0.2,
        instrumentation_confidence=95.0,
        num_passes=50
    )
    
    assert res["station_id"] == "S1"
    assert res["passes_count"] == 50
    assert len(res["passes"]) == 50
    assert len(res["envelope"]) == 5
    
    # Check that envelope lowerBand90 <= mean <= upperBand90
    for env in res["envelope"]:
        assert env["lowerBand90"] <= env["mean"] <= env["upperBand90"]
        assert env["stdDev"] >= 0

def test_monte_carlo_uncertainty_passes_degraded():
    res = generate_monte_carlo_uncertainty_passes(
        station_id="S3",
        baseline_cycle_time=54.0,
        current_cycle_time=82.0,
        current_variance=4.5,
        instrumentation_confidence=80.0,
        num_passes=50
    )
    
    assert res["station_id"] == "S3"
    assert len(res["passes"]) == 50
    # Degraded station envelope should show upward drift at horizon 20 min
    t0_env = next(e for e in res["envelope"] if e["timeMin"] == 0)
    t20_env = next(e for e in res["envelope"] if e["timeMin"] == 20)
    assert t20_env["mean"] >= t0_env["mean"]
