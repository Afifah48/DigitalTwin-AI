from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from ..models.enums import StationId


class SensorMetadata(BaseModel):
    station_id: StationId
    sensor_id: str
    sensor_type: str  # 'TEMPERATURE', 'VIBRATION', 'CURRENT', 'CYCLE_TIMER', 'OPTICAL'
    sampling_rate_hz: float
    instrumentation_density: str
    is_available: bool = True
    quality_score: float = 1.0


# Factory standard instrumentation blueprint
STATION_SENSOR_SPECS: Dict[StationId, List[Dict[str, Any]]] = {
    StationId.S1: [
        {"sensor_id": "S1_TEMP_WELD_01", "sensor_type": "TEMPERATURE", "sampling_rate_hz": 10.0, "density": "HIGH"},
        {"sensor_id": "S1_VIB_ROBOT_01", "sensor_type": "VIBRATION", "sampling_rate_hz": 100.0, "density": "HIGH"},
        {"sensor_id": "S1_CURR_WELD_01", "sensor_type": "CURRENT", "sampling_rate_hz": 50.0, "density": "HIGH"},
        {"sensor_id": "S1_CYCLE_TIMER_01", "sensor_type": "CYCLE_TIMER", "sampling_rate_hz": 1.0, "density": "HIGH"},
    ],
    StationId.S2: [
        {"sensor_id": "S2_TEMP_OVEN_01", "sensor_type": "TEMPERATURE", "sampling_rate_hz": 10.0, "density": "HIGH"},
        {"sensor_id": "S2_VIB_BELL_01", "sensor_type": "VIBRATION", "sampling_rate_hz": 100.0, "density": "HIGH"},
        {"sensor_id": "S2_CURR_ATOM_01", "sensor_type": "CURRENT", "sampling_rate_hz": 50.0, "density": "HIGH"},
        {"sensor_id": "S2_CYCLE_TIMER_01", "sensor_type": "CYCLE_TIMER", "sampling_rate_hz": 1.0, "density": "HIGH"},
    ],
    StationId.S3: [
        {"sensor_id": "S3_TEMP_DECK_01", "sensor_type": "TEMPERATURE", "sampling_rate_hz": 10.0, "density": "HIGH"},
        {"sensor_id": "S3_VIB_SPINDLE_01", "sensor_type": "VIBRATION", "sampling_rate_hz": 100.0, "density": "HIGH"},
        {"sensor_id": "S3_CURR_SPINDLE_01", "sensor_type": "CURRENT", "sampling_rate_hz": 50.0, "density": "HIGH"},
        {"sensor_id": "S3_CYCLE_TIMER_01", "sensor_type": "CYCLE_TIMER", "sampling_rate_hz": 1.0, "density": "HIGH"},
    ],
    StationId.S4: [
        {"sensor_id": "S4_TEMP_INVERTER_01", "sensor_type": "TEMPERATURE", "sampling_rate_hz": 10.0, "density": "MEDIUM"},
        {"sensor_id": "S4_VIB_MANIP_01", "sensor_type": "VIBRATION", "sampling_rate_hz": 50.0, "density": "MEDIUM"},
        {"sensor_id": "S4_CURR_HV_01", "sensor_type": "CURRENT", "sampling_rate_hz": 20.0, "density": "MEDIUM"},
        {"sensor_id": "S4_CYCLE_TIMER_01", "sensor_type": "CYCLE_TIMER", "sampling_rate_hz": 1.0, "density": "MEDIUM"},
    ],
    StationId.S5: [
        {"sensor_id": "S5_TEMP_CABIN_01", "sensor_type": "TEMPERATURE", "sampling_rate_hz": 2.0, "density": "LOW"},
        {"sensor_id": "S5_VIB_ASSIST_01", "sensor_type": "VIBRATION", "sampling_rate_hz": 10.0, "density": "LOW"},
        {"sensor_id": "S5_CURR_LIFT_01", "sensor_type": "CURRENT", "sampling_rate_hz": 5.0, "density": "LOW"},
        {"sensor_id": "S5_CYCLE_TIMER_01", "sensor_type": "CYCLE_TIMER", "sampling_rate_hz": 1.0, "density": "LOW"},
    ],
    StationId.S6: [
        {"sensor_id": "S6_OPTICAL_METRO_01", "sensor_type": "OPTICAL", "sampling_rate_hz": 100.0, "density": "HIGH"},
        {"sensor_id": "S6_VIB_DYNO_01", "sensor_type": "VIBRATION", "sampling_rate_hz": 100.0, "density": "HIGH"},
        {"sensor_id": "S6_CURR_BENCH_01", "sensor_type": "CURRENT", "sampling_rate_hz": 50.0, "density": "HIGH"},
        {"sensor_id": "S6_CYCLE_TIMER_01", "sensor_type": "CYCLE_TIMER", "sampling_rate_hz": 1.0, "density": "HIGH"},
    ],
}


def get_station_sensor_catalog() -> List[SensorMetadata]:
    """Generates the full catalog of sensor metadata across all 6 stations."""
    catalog = []
    for st_id, specs in STATION_SENSOR_SPECS.items():
        for s in specs:
            catalog.append(
                SensorMetadata(
                    station_id=st_id,
                    sensor_id=s["sensor_id"],
                    sensor_type=s["sensor_type"],
                    sampling_rate_hz=s["sampling_rate_hz"],
                    instrumentation_density=s["density"],
                    is_available=True,
                    quality_score=1.0,
                )
            )
    return catalog
