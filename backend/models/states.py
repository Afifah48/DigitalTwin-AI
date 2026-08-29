from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from .enums import StationId, BufferId, MachineState, ExposureLevel, VehicleModel, InstrumentationLevel


class TelemetryState(BaseModel):
    cycle_time: float = Field(default=0.0, description="Cycle time in seconds (nominal ~50-55s)")
    baseline_cycle_time: float = Field(default=54.0, description="DES baseline cycle time in seconds")
    utilization: float = Field(default=0.0, description="Station utilization percentage (0 - 100%)")
    queue_length: int = Field(default=0, description="Vehicles waiting in upstream queue/buffer")
    buffer_max: int = Field(default=5, description="Maximum buffer capacity")
    wip: int = Field(default=0, description="Work in progress in and immediately ahead of station")
    temperature: float = Field(default=25.0, description="Station temperature in °C")
    vibration: float = Field(default=1.0, description="Station vibration mm/s RMS")
    motor_current: float = Field(default=12.0, description="Motor current in Amperes (A)")
    current_variance: float = Field(default=0.1, description="Motor current variance A^2")
    machine_state: MachineState = Field(default=MachineState.IDLE, description="Current machine operational state")
    confidence: float = Field(default=95.0, description="Telemetry confidence percentage (0-100%)")
    instrumentation_level: InstrumentationLevel = Field(default=InstrumentationLevel.HIGH, description="Sensor instrumentation level")


class StationState(BaseModel):
    id: StationId
    name: str
    sub_title: str = ""
    description: str = ""
    color: str = "#38BDF8"
    active_tooling: str = ""
    sensor_count: int = 64
    spatial_neighbors: List[StationId] = Field(default_factory=list)
    telemetry: TelemetryState = Field(default_factory=TelemetryState)
    total_processed: int = 0
    total_busy_time: float = 0.0
    total_idle_time: float = 0.0
    total_blocked_time: float = 0.0
    total_starved_time: float = 0.0
    total_down_time: float = 0.0
    blocked_count: int = 0
    starved_count: int = 0
    down_count: int = 0


class BufferState(BaseModel):
    id: BufferId
    upstream_station_id: StationId
    downstream_station_id: StationId
    capacity: int = 5
    current_occupancy: int = 0
    vehicle_ids: List[str] = Field(default_factory=list)
    peak_occupancy: int = 0
    total_entries: int = 0
    total_exits: int = 0


class VehiclePass(BaseModel):
    station_id: StationId
    entered_at: float
    completed_at: float
    actual_cycle_time: float
    expected_cycle_time: float
    torque_variance: Optional[float] = None
    thermal_delta: Optional[float] = None
    exposure_flag: ExposureLevel = ExposureLevel.LOW
    deviation_at_pass: float = 0.0


class VehicleState(BaseModel):
    id: str
    model: VehicleModel = VehicleModel.APEX_GT_EV
    color: str = "#38BDF8"
    color_name: str = "Cyber Blue"
    vin: str = ""
    current_station_id: Optional[StationId] = None
    current_buffer_id: Optional[BufferId] = None
    progress_in_station: float = 0.0
    created_at: float = 0.0
    completed_at: Optional[float] = None
    total_transit_time: float = 0.0
    quality_exposure: ExposureLevel = ExposureLevel.LOW
    history: List[VehiclePass] = Field(default_factory=list)
    is_completed: bool = False


class FactoryState(BaseModel):
    simulation_time: float = 0.0
    target_takt_time: float = 54.0
    stations: Dict[StationId, StationState] = Field(default_factory=dict)
    buffers: Dict[BufferId, BufferState] = Field(default_factory=dict)
    active_vehicles: Dict[str, VehicleState] = Field(default_factory=dict)
    completed_vehicles: List[VehicleState] = Field(default_factory=list)
    total_throughput: int = 0
    throughput_uph: float = 0.0
    average_cycle_time: float = 0.0
    system_utilization: float = 0.0
