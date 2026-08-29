import os
import json
import csv
import tempfile
import pytest
from backend.twin.digital_twin import DigitalTwin
from backend.config.factory_config import get_default_factory_config
from backend.models.enums import EventType, StationId


def test_throughput_and_uph_calculations():
    """Verify that UPH, average cycle time, and system metrics are correctly computed."""
    config = get_default_factory_config()
    twin = DigitalTwin(config=config, seed=42)
    state = twin.simulate(3600.0)  # 1 hour simulation

    assert state.total_throughput > 0
    # For a 1-hour simulation, throughput_uph should equal total_throughput
    assert state.throughput_uph == pytest.approx(float(state.total_throughput), 0.1)
    assert 50.0 <= state.average_cycle_time <= 60.0
    assert 0.0 <= state.system_utilization <= 100.0


def test_event_logging_and_export():
    """Verify that all discrete events are logged with correct attributes and exportable."""
    config = get_default_factory_config()
    twin = DigitalTwin(config=config, seed=42)
    state = twin.simulate(600.0)

    events = twin.get_events()
    assert len(events) > 0

    # Verify processing complete event schema
    proc_events = [e for e in events if e.event_type == EventType.PROCESSING_COMPLETE]
    assert len(proc_events) > 0

    sample_ev = proc_events[0]
    assert sample_ev.timestamp >= 0.0
    assert sample_ev.vehicle_id is not None
    assert sample_ev.station_id is not None
    assert sample_ev.cycle_time is not None
    assert sample_ev.cycle_time > 0.0
    assert sample_ev.queue_before is not None
    assert sample_ev.queue_after is not None
    assert sample_ev.buffer_before is not None
    assert sample_ev.buffer_after is not None

    # Test export to JSON and CSV
    with tempfile.TemporaryDirectory() as tmp_dir:
        json_path = os.path.join(tmp_dir, "events.json")
        csv_path = os.path.join(tmp_dir, "events.csv")

        twin.export_event_log_json(json_path)
        assert os.path.exists(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert len(data) == len(events)

        twin.export_event_log_csv(csv_path)
        assert os.path.exists(csv_path)
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == len(events)
            assert "cycle_time" in rows[0]
            assert "queue_before" in rows[0]
