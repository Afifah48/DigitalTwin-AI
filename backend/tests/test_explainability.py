import pytest
from backend.app.explainability.service import compute_explainability_attribution

def test_explainability_attribution_structure():
    telemetry_snap = {
        "stations": {
            "S1": {"cycle_time": 52.0, "cycle_time_delta": 0.0, "current_variance": 0.1, "temperature": 45.0, "vibration": 0.9, "queue_length": 1, "wip_count": 2},
            "S2": {"cycle_time": 54.0, "cycle_time_delta": 0.0, "current_variance": 0.2, "temperature": 46.0, "vibration": 1.0, "queue_length": 5, "wip_count": 6},
            "S3": {"cycle_time": 78.5, "cycle_time_delta": 24.5, "current_variance": 4.1, "temperature": 54.0, "vibration": 3.8, "queue_length": 3, "wip_count": 4},
            "S4": {"cycle_time": 51.0, "cycle_time_delta": 0.0, "current_variance": 0.1, "temperature": 44.0, "vibration": 0.8, "queue_length": 0, "wip_count": 0},
            "S5": {"cycle_time": 53.0, "cycle_time_delta": 0.0, "current_variance": 0.1, "temperature": 45.0, "vibration": 0.9, "queue_length": 0, "wip_count": 0},
            "S6": {"cycle_time": 55.0, "cycle_time_delta": 0.0, "current_variance": 0.1, "temperature": 45.0, "vibration": 0.9, "queue_length": 0, "wip_count": 0}
        }
    }
    
    res = compute_explainability_attribution(
        station_id="S3",
        telemetry_snapshot=telemetry_snap
    )
    
    assert res["station_id"] == "S3"
    assert "featureAttributions" in res
    assert len(res["featureAttributions"]) >= 4
    
    # Check feature importance order and bounds
    for feat in res["featureAttributions"]:
        assert 0 <= feat["importance"] <= 100
        assert feat["impact"] in ["HIGH", "MEDIUM", "LOW"]
        
    assert "spatialAttribution" in res
    assert len(res["spatialAttribution"]) == 6
    total_spatial_weight = sum(s["influenceWeight"] for s in res["spatialAttribution"])
    assert 95 <= total_spatial_weight <= 105 # Check normalized sum
    
    assert "temporalAttribution" in res
    assert len(res["temporalAttribution"]) == 4
