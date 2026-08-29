from enum import Enum


class StationId(str, Enum):
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"
    S4 = "S4"
    S5 = "S5"
    S6 = "S6"


class BufferId(str, Enum):
    B12 = "B12"
    B23 = "B23"
    B34 = "B34"
    B45 = "B45"
    B56 = "B56"


class MachineState(str, Enum):
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    BLOCKED = "BLOCKED"
    STARVED = "STARVED"
    DOWN = "DOWN"
    MAINTENANCE = "MAINTENANCE"
    MICRO_STOP = "MICRO_STOP"


class ExposureLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class VehicleModel(str, Enum):
    APEX_GT_EV = "APEX GT-EV"
    NEXUS_SEDAN = "NEXUS SEDAN"
    VALENCE_SUV = "VALENCE SUV"
    HORIZON_CROSS = "HORIZON CROSS"


class InstrumentationLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EventType(str, Enum):
    VEHICLE_CREATED = "VEHICLE_CREATED"
    QUEUE_ENTER = "QUEUE_ENTER"
    PROCESSING_START = "PROCESSING_START"
    PROCESSING_COMPLETE = "PROCESSING_COMPLETE"
    STATE_CHANGE = "STATE_CHANGE"
    BLOCKED_START = "BLOCKED_START"
    BLOCKED_END = "BLOCKED_END"
    STARVED_START = "STARVED_START"
    STARVED_END = "STARVED_END"
    DOWN_START = "DOWN_START"
    DOWN_END = "DOWN_END"
    BUFFER_ENTER = "BUFFER_ENTER"
    BUFFER_EXIT = "BUFFER_EXIT"
    VEHICLE_FINISHED = "VEHICLE_FINISHED"
