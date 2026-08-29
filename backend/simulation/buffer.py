from typing import List, Optional, Callable
import simpy
from ..models.enums import BufferId, StationId, EventType
from ..models.states import BufferState, VehicleState
from ..models.events import FactoryEvent


class SimBuffer:
    """
    Finite-capacity discrete-event buffer between sequential stations.
    Leverages SimPy Store with bounded capacity to enforce physical push/pull limits.
    """

    def __init__(
        self,
        env: simpy.Environment,
        buffer_id: BufferId,
        upstream_station_id: StationId,
        downstream_station_id: StationId,
        capacity: int = 5,
        event_logger: Optional[Callable[[FactoryEvent], None]] = None,
    ):
        self.env = env
        self.buffer_id = buffer_id
        self.upstream_station_id = upstream_station_id
        self.downstream_station_id = downstream_station_id
        self.capacity = capacity
        self.store = simpy.Store(env, capacity=capacity)
        self.vehicle_ids: List[str] = []
        self.peak_occupancy: int = 0
        self.total_entries: int = 0
        self.total_exits: int = 0
        self.event_logger = event_logger

    @property
    def current_occupancy(self) -> int:
        return len(self.store.items)

    @property
    def is_full(self) -> bool:
        return self.current_occupancy >= self.capacity

    @property
    def is_empty(self) -> bool:
        return self.current_occupancy == 0

    def put(self, vehicle: VehicleState):
        """
        Pushes a vehicle into the buffer.
        Yields if buffer is at full capacity (causing upstream process to wait/block).
        """
        occ_before = self.current_occupancy
        req = self.store.put(vehicle)
        yield req

        occ_after = self.current_occupancy
        self.vehicle_ids.append(vehicle.id)
        vehicle.current_buffer_id = self.buffer_id
        self.total_entries += 1
        if occ_after > self.peak_occupancy:
            self.peak_occupancy = occ_after

        if self.event_logger:
            self.event_logger(
                FactoryEvent(
                    timestamp=self.env.now,
                    event_type=EventType.BUFFER_ENTER,
                    buffer_id=self.buffer_id,
                    vehicle_id=vehicle.id,
                    buffer_before=occ_before,
                    buffer_after=occ_after,
                    details={"capacity": self.capacity, "vehicle_model": vehicle.model.value},
                )
            )

    def get(self):
        """
        Pulls a vehicle from the buffer.
        Yields if buffer is empty (causing downstream process to wait/starve).
        """
        occ_before = self.current_occupancy
        vehicle: VehicleState = yield self.store.get()
        occ_after = self.current_occupancy

        if vehicle.id in self.vehicle_ids:
            self.vehicle_ids.remove(vehicle.id)
        vehicle.current_buffer_id = None
        self.total_exits += 1

        if self.event_logger:
            self.event_logger(
                FactoryEvent(
                    timestamp=self.env.now,
                    event_type=EventType.BUFFER_EXIT,
                    buffer_id=self.buffer_id,
                    vehicle_id=vehicle.id,
                    buffer_before=occ_before,
                    buffer_after=occ_after,
                    details={"capacity": self.capacity},
                )
            )

        return vehicle

    def get_state(self) -> BufferState:
        return BufferState(
            id=self.buffer_id,
            upstream_station_id=self.upstream_station_id,
            downstream_station_id=self.downstream_station_id,
            capacity=self.capacity,
            current_occupancy=self.current_occupancy,
            vehicle_ids=list(self.vehicle_ids),
            peak_occupancy=self.peak_occupancy,
            total_entries=self.total_entries,
            total_exits=self.total_exits,
        )
