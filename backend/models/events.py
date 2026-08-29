from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from .enums import EventType, StationId, BufferId, MachineState


class FactoryEvent(BaseModel):
    timestamp: float = Field(..., description="Simulation time in seconds when event occurred")
    event_type: EventType = Field(..., description="Classification of discrete event")
    station_id: Optional[StationId] = Field(default=None, description="Associated station if applicable")
    buffer_id: Optional[BufferId] = Field(default=None, description="Associated buffer if applicable")
    vehicle_id: Optional[str] = Field(default=None, description="Associated vehicle identifier")
    cycle_time: Optional[float] = Field(default=None, description="Station cycle time in seconds")
    machine_state: Optional[MachineState] = Field(default=None, description="Machine state at time of event")
    queue_before: Optional[int] = Field(default=None, description="Upstream queue length before event")
    queue_after: Optional[int] = Field(default=None, description="Upstream queue length after event")
    buffer_before: Optional[int] = Field(default=None, description="Buffer occupancy before event")
    buffer_after: Optional[int] = Field(default=None, description="Buffer occupancy after event")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional context or sensor metadata")
