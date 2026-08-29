from typing import List, Dict, Optional, Callable
import simpy
import numpy as np
from ..models.enums import StationId, BufferId
from ..models.states import FactoryState, StationState, BufferState, VehicleState
from ..models.events import FactoryEvent
from ..config.factory_config import FactoryConfig, get_default_factory_config
from .buffer import SimBuffer
from .station import SimStation
from .vehicle_generator import VehicleGenerator


class FactoryEngine:
    """
    SimPy Discrete-Event Simulation Engine for 6-station finite-buffer automotive line.
    """

    def __init__(
        self,
        config: Optional[FactoryConfig] = None,
        seed: Optional[int] = None,
        event_callback: Optional[Callable[[FactoryEvent], None]] = None,
    ):
        self.config = config or get_default_factory_config()
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.event_callback = event_callback

        self.env = simpy.Environment()
        self.events: List[FactoryEvent] = []
        self.completed_vehicles: List[VehicleState] = []

        # Feeder queue before S1
        self.input_queue = simpy.Store(self.env)
        self.generator = VehicleGenerator(
            env=self.env,
            output_queue=self.input_queue,
            arrival_interval=self.config.input_arrival_interval,
            arrival_std=self.config.input_arrival_std,
            event_logger=self._record_event,
            rng=self.rng,
        )

        # Buffers: B12, B23, B34, B45, B56
        self.buffers: Dict[BufferId, SimBuffer] = {}
        for buf_id, b_cfg in self.config.buffer_configs.items():
            self.buffers[buf_id] = SimBuffer(
                env=self.env,
                buffer_id=buf_id,
                upstream_station_id=b_cfg.upstream_station_id,
                downstream_station_id=b_cfg.downstream_station_id,
                capacity=b_cfg.capacity,
                event_logger=self._record_event,
            )

        # Stations: S1 to S6
        self.stations: Dict[StationId, SimStation] = {}
        station_order = [
            StationId.S1,
            StationId.S2,
            StationId.S3,
            StationId.S4,
            StationId.S5,
            StationId.S6,
        ]

        buffer_mapping = {
            StationId.S1: (None, self.buffers[BufferId.B12]),
            StationId.S2: (self.buffers[BufferId.B12], self.buffers[BufferId.B23]),
            StationId.S3: (self.buffers[BufferId.B23], self.buffers[BufferId.B34]),
            StationId.S4: (self.buffers[BufferId.B34], self.buffers[BufferId.B45]),
            StationId.S5: (self.buffers[BufferId.B45], self.buffers[BufferId.B56]),
            StationId.S6: (self.buffers[BufferId.B56], None),
        }

        for st_id in station_order:
            st_cfg = self.config.station_configs[st_id]
            up_buf, down_buf = buffer_mapping[st_id]
            self.stations[st_id] = SimStation(
                env=self.env,
                config=st_cfg,
                upstream_buffer=up_buf,
                downstream_buffer=down_buf,
                input_queue=self.input_queue if st_id == StationId.S1 else None,
                completed_sink=self._on_vehicle_completed if st_id == StationId.S6 else None,
                event_logger=self._record_event,
                rng=self.rng,
            )

    def _record_event(self, event: FactoryEvent):
        self.events.append(event)
        if self.event_callback:
            self.event_callback(event)

    def _on_vehicle_completed(self, vehicle: VehicleState):
        self.completed_vehicles.append(vehicle)

    def step_until(self, target_time: float):
        """Advances the simulation clock to target_time."""
        self.env.run(until=target_time)

    def run(self, duration_seconds: float) -> FactoryState:
        """Runs the discrete-event simulation for the specified duration and returns FactoryState."""
        self.env.run(until=duration_seconds)
        return self.get_factory_state()

    def get_factory_state(self) -> FactoryState:
        station_states: Dict[StationId, StationState] = {
            st_id: st.get_state() for st_id, st in self.stations.items()
        }
        buffer_states: Dict[BufferId, BufferState] = {
            buf_id: buf.get_state() for buf_id, buf in self.buffers.items()
        }

        total_throughput = len(self.completed_vehicles)
        sim_time = max(1.0, float(self.env.now))
        # Units Per Hour (UPH)
        uph = (total_throughput / (sim_time / 3600.0)) if sim_time > 0 else 0.0

        # Mean cycle time across completed vehicles or stations
        if total_throughput > 0:
            avg_transit = sum(v.total_transit_time for v in self.completed_vehicles) / total_throughput
            avg_cycle = avg_transit / 6.0  # Normalized per station
        else:
            avg_cycle = sum(st.telemetry.cycle_time for st in station_states.values()) / 6.0

        avg_util = sum(st.telemetry.utilization for st in station_states.values()) / 6.0

        # Active vehicles in line
        active_map: Dict[str, VehicleState] = {}
        for v in self.generator.active_vehicles.values():
            if not v.is_completed:
                active_map[v.id] = v

        return FactoryState(
            simulation_time=round(self.env.now, 2),
            target_takt_time=self.config.target_takt_time,
            stations=station_states,
            buffers=buffer_states,
            active_vehicles=active_map,
            completed_vehicles=list(self.completed_vehicles),
            total_throughput=total_throughput,
            throughput_uph=round(uph, 1),
            average_cycle_time=round(avg_cycle, 2),
            system_utilization=round(avg_util, 1),
        )
