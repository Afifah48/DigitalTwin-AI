import pytest
from fastapi.testclient import TestClient
from backend.api import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "version" in data

def test_health_endpoints():
    r1 = client.get("/health")
    assert r1.status_code == 200
    assert r1.json()["status"] == "healthy"

    r2 = client.get("/api/health")
    assert r2.status_code == 200
    assert r2.json()["status"] == "healthy"

def test_factory_state_endpoint():
    response = client.get("/api/factory-state")
    assert response.status_code == 200
    data = response.json()
    assert "stations" in data
    assert "vehicles" in data
    assert "decision" in data
    assert len(data["stations"]) == 6

def test_explainability_endpoint():
    response = client.get("/api/explainability?station_id=S3")
    assert response.status_code == 200
    data = response.json()
    assert "featureAttributions" in data
    assert "spatialAttribution" in data
    assert "temporalAttribution" in data

def test_uncertainty_endpoint():
    response = client.get("/api/uncertainty?station_id=S3")
    assert response.status_code == 200
    data = response.json()
    assert "passes" in data
    assert len(data["passes"]) == 50

def test_trajectory_endpoint():
    response = client.get("/api/trajectory?station_id=S3")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

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

