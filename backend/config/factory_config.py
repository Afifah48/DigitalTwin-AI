from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from ..models.enums import StationId, BufferId, InstrumentationLevel


class SensorConfig(BaseModel):
    sensor_count: int = 64
    base_temperature: float = 40.0
    temperature_std: float = 1.5
    base_vibration: float = 1.2
    vibration_std: float = 0.2
    base_motor_current: float = 14.0
    motor_current_std: float = 0.8
    base_variance: float = 0.15
    confidence: float = 95.0
    instrumentation_level: InstrumentationLevel = InstrumentationLevel.HIGH


class StationConfig(BaseModel):
    station_id: StationId
    name: str
    sub_title: str = ""
    description: str = ""
    color: str = "#38BDF8"
    active_tooling: str = ""
    baseline_cycle_time: float = 54.0
    cycle_time_std: float = 1.0
    min_cycle_time: float = 10.0
    failure_probability: float = 0.0  # Probability of breakdown per vehicle cycle (0.0 = deterministic)
    repair_time: float = 120.0        # Mean repair time in seconds if failure occurs
    repair_time_std: float = 20.0
    sensor_config: SensorConfig = Field(default_factory=SensorConfig)
    spatial_neighbors: List[StationId] = Field(default_factory=list)


class BufferConfig(BaseModel):
    buffer_id: BufferId
    upstream_station_id: StationId
    downstream_station_id: StationId
    capacity: int = 5


class FactoryConfig(BaseModel):
    target_takt_time: float = 54.0
    input_arrival_interval: float = 54.0
    input_arrival_std: float = 0.0
    station_configs: Dict[StationId, StationConfig] = Field(default_factory=dict)
    buffer_configs: Dict[BufferId, BufferConfig] = Field(default_factory=dict)
    default_buffer_capacity: int = 5


def get_default_factory_config() -> FactoryConfig:
    """Returns the realistic baseline automotive factory configuration matching the frontend specification."""
    station_configs = {
        StationId.S1: StationConfig(
            station_id=StationId.S1,
            name="FRAMING",
            sub_title="Robotic Underbody & Side Ring Spot Welding",
            description="18 high-precision KUKA robotic weld arms fastening unibody floorpan and pillars to 0.05mm tolerance.",
            color="#38BDF8",
            active_tooling="KUKA KR-QUANTEC Spot Welder Cell #04",
            baseline_cycle_time=52.0,
            cycle_time_std=1.0,
            failure_probability=0.0,
            repair_time=120.0,
            sensor_config=SensorConfig(
                sensor_count=64,
                base_temperature=42.1,
                base_vibration=1.4,
                base_motor_current=14.2,
                base_variance=0.12,
                confidence=96.0,
                instrumentation_level=InstrumentationLevel.HIGH,
            ),
            spatial_neighbors=[StationId.S2],
        ),
        StationId.S2: StationConfig(
            station_id=StationId.S2,
            name="PAINT",
            sub_title="Electrocoat, Primer & Clearcoat Robot Cells",
            description="Multi-stage immersion bath and 12 electrostatic rotary bell atomizers with heated drying ovens.",
            color="#06B6D4",
            active_tooling="Dürr EcoBell3 High-Rotation Atomizer",
            baseline_cycle_time=54.0,
            cycle_time_std=1.2,
            failure_probability=0.0,
            repair_time=180.0,
            sensor_config=SensorConfig(
                sensor_count=88,
                base_temperature=78.4,
                base_vibration=2.1,
                base_motor_current=18.5,
                base_variance=0.45,
                confidence=94.0,
                instrumentation_level=InstrumentationLevel.HIGH,
            ),
            spatial_neighbors=[StationId.S1, StationId.S3],
        ),
        StationId.S3: StationConfig(
            station_id=StationId.S3,
            name="CHASSIS MARRIAGE",
            sub_title="Decking & Automated High-Torque Multi-Spindle",
            description="Heavy AGV lifters docking battery pack and front/rear suspension subframes to BIW body shell.",
            color="#F59E0B",
            active_tooling="Atlas Copco Tensor Reversible 8-Spindle Synchronizer",
            baseline_cycle_time=54.0,
            cycle_time_std=1.5,
            failure_probability=0.0,
            repair_time=150.0,
            sensor_config=SensorConfig(
                sensor_count=112,
                base_temperature=64.8,
                base_vibration=2.4,
                base_motor_current=24.0,
                base_variance=0.35,
                confidence=98.0,
                instrumentation_level=InstrumentationLevel.HIGH,
            ),
            spatial_neighbors=[StationId.S2, StationId.S4],
        ),
        StationId.S4: StationConfig(
            station_id=StationId.S4,
            name="POWERTRAIN",
            sub_title="High-Voltage Harness & Drive Inverter Assembly",
            description="Automated 800V high-voltage busbar fastening, coolant loop coupling, and inverter bus diagnostics.",
            color="#818CF8",
            active_tooling="Stäubli TX2-90 Cleanroom High-Voltage Manipulator",
            baseline_cycle_time=51.0,
            cycle_time_std=1.0,
            failure_probability=0.0,
            repair_time=100.0,
            sensor_config=SensorConfig(
                sensor_count=52,
                base_temperature=36.2,
                base_vibration=1.1,
                base_motor_current=11.8,
                base_variance=0.18,
                confidence=82.0,
                instrumentation_level=InstrumentationLevel.MEDIUM,
            ),
            spatial_neighbors=[StationId.S3, StationId.S5],
        ),
        StationId.S5: StationConfig(
            station_id=StationId.S5,
            name="INTERIOR & WIRING",
            sub_title="Cockpit Module, Harness Loom & Acoustic Lining",
            description="Collaborative human-robot cell mounting instrument panel cross-car beam and floor wiring harness.",
            color="#A78BFA",
            active_tooling="Universal Robots UR10e Ergonomic Lift Assist",
            baseline_cycle_time=53.0,
            cycle_time_std=1.2,
            failure_probability=0.0,
            repair_time=90.0,
            sensor_config=SensorConfig(
                sensor_count=28,
                base_temperature=24.5,
                base_vibration=0.8,
                base_motor_current=8.2,
                base_variance=0.25,
                confidence=58.0,
                instrumentation_level=InstrumentationLevel.LOW,
            ),
            spatial_neighbors=[StationId.S4, StationId.S6],
        ),
        StationId.S6: StationConfig(
            station_id=StationId.S6,
            name="FINAL INSPECTION",
            sub_title="Optical ADAS Calibration, EOL Tester & Roll Bench",
            description="Dynamic 3D optical laser scanning, roll-and-brake dynamometer testing, and ADAS camera matrix alignment.",
            color="#34D399",
            active_tooling="Perceptron 3D HeliMetrix In-Line Metrology Station",
            baseline_cycle_time=55.0,
            cycle_time_std=1.0,
            failure_probability=0.0,
            repair_time=60.0,
            sensor_config=SensorConfig(
                sensor_count=96,
                base_temperature=22.8,
                base_vibration=0.6,
                base_motor_current=9.4,
                base_variance=0.08,
                confidence=95.0,
                instrumentation_level=InstrumentationLevel.HIGH,
            ),
            spatial_neighbors=[StationId.S5],
        ),
    }

    buffer_configs = {
        BufferId.B12: BufferConfig(
            buffer_id=BufferId.B12,
            upstream_station_id=StationId.S1,
            downstream_station_id=StationId.S2,
            capacity=5,
        ),
        BufferId.B23: BufferConfig(
            buffer_id=BufferId.B23,
            upstream_station_id=StationId.S2,
            downstream_station_id=StationId.S3,
            capacity=5,
        ),
        BufferId.B34: BufferConfig(
            buffer_id=BufferId.B34,
            upstream_station_id=StationId.S3,
            downstream_station_id=StationId.S4,
            capacity=5,
        ),
        BufferId.B45: BufferConfig(
            buffer_id=BufferId.B45,
            upstream_station_id=StationId.S4,
            downstream_station_id=StationId.S5,
            capacity=5,
        ),
        BufferId.B56: BufferConfig(
            buffer_id=BufferId.B56,
            upstream_station_id=StationId.S5,
            downstream_station_id=StationId.S6,
            capacity=5,
        ),
    }

    return FactoryConfig(
        target_takt_time=54.0,
        input_arrival_interval=54.0,
        input_arrival_std=0.0,
        station_configs=station_configs,
        buffer_configs=buffer_configs,
        default_buffer_capacity=5,
    )
