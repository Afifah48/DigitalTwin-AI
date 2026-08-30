import pytest
from fastapi.testclient import TestClient
from backend.api import app

client = TestClient(app)

def test_get_scenarios_endpoint():
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    
    data = response.json()
    assert "scenarios" in data
    
    scenarios = data["scenarios"]
    assert len(scenarios) > 0
    assert len(scenarios) <= 4
    
    # Check baseline (NO_ACTION) exists
    has_baseline = any(s["id"] == "NO_ACTION" for s in scenarios)
    assert has_baseline, "Baseline NO_ACTION scenario missing"
    
    # Check at least one recommended candidate
    has_recommended = any(s["isRecommended"] is True for s in scenarios)
    assert has_recommended, "No recommended scenario returned"
    
    # Check schema conformance
    for s in scenarios:
        assert "id" in s
        assert "throughputDeltaUPH" in s
        assert "riskDelta" in s
        assert "queueLengthT20" in s
        assert "affectedStations" in s
        assert "bottleneckMigrated" in s
