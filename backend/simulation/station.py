from typing import Optional, Callable, Dict, Any, List
import simpy
import numpy as np
from ..models.enums import StationId, MachineState, EventType, ExposureLevel
from ..models.states import StationState, TelemetryState, VehicleState, VehiclePass
from ..models.events import FactoryEvent
from ..config.factory_config import StationConfig
from .buffer import SimBuffer


class SimStation:
    """
    Discrete-event station model.
    Pulls vehicles from upstream buffer, performs cycle-time processing with potential
    failure/downtime events, and pushes to downstream finite buffer with natural blocking.
    Supports dynamic scenario parameter modulation over simulation time.
    """

    def __init__(
        self,
        env: simpy.Environment,
        config: StationConfig,
        upstream_buffer: Optional[SimBuffer] = None,
        downstream_buffer: Optional[SimBuffer] = None,
        input_queue: Optional[simpy.Store] = None,
        completed_sink: Optional[Callable[[VehicleState], None]] = None,
        event_logger: Optional[Callable[[FactoryEvent], None]] = None,
        rng: Optional[np.random.Generator] = None,
    ):
        self.env = env
        self.config = config
        self.station_id = config.station_id
        self.upstream_buffer = upstream_buffer
        self.downstream_buffer = downstream_buffer
        self.input_queue = input_queue
        self.completed_sink = completed_sink
        self.event_logger = event_logger
        self.rng = rng if rng is not None else np.random.default_rng()

        self.current_vehicle: Optional[VehicleState] = None
        self.machine_state: MachineState = MachineState.IDLE
        self.last_cycle_time: float = config.baseline_cycle_time

        # Dynamic scenario modifiers: functions f(t: float) -> float
        self.dynamic_baseline_cycle_time: Optional[Callable[[float], float]] = None
        self.dynamic_cycle_time_std: Optional[Callable[[float], float]] = None
        self.dynamic_failure_probability: Optional[Callable[[float], float]] = None
        self.dynamic_vibration_offset: Optional[Callable[[float], float]] = None
        self.dynamic_current_variance_offset: Optional[Callable[[float], float]] = None
        self.dynamic_temperature_offset: Optional[Callable[[float], float]] = None

        # Accumulator metrics
        self.total_processed: int = 0
        self.total_busy_time: float = 0.0
        self.total_idle_time: float = 0.0
        self.total_blocked_time: float = 0.0
        self.total_starved_time: float = 0.0
        self.total_down_time: float = 0.0

        self.blocked_count: int = 0
        self.starved_count: int = 0
        self.down_count: int = 0

        # State tracking timestamps
        self._last_state_change_time: float = 0.0
        self._action_process = self.env.process(self._run_loop())

    def get_effective_baseline_cycle_time(self, t: Optional[float] = None) -> float:
        curr_t = self.env.now if t is None else t
        if self.dynamic_baseline_cycle_time is not None:
            return float(self.dynamic_baseline_cycle_time(curr_t))
        return float(self.config.baseline_cycle_time)

    def get_effective_cycle_time_std(self, t: Optional[float] = None) -> float:
        curr_t = self.env.now if t is None else t
        if self.dynamic_cycle_time_std is not None:
            return float(self.dynamic_cycle_time_std(curr_t))
        return float(self.config.cycle_time_std)

    def get_effective_failure_probability(self, t: Optional[float] = None) -> float:
        curr_t = self.env.now if t is None else t
        if self.dynamic_failure_probability is not None:
            return float(self.dynamic_failure_probability(curr_t))
        return float(self.config.failure_probability)

    def _log_event(
        self,
        event_type: EventType,
        vehicle_id: Optional[str] = None,
        cycle_time: Optional[float] = None,
        queue_before: Optional[int] = None,
        queue_after: Optional[int] = None,
        buffer_before: Optional[int] = None,
        buffer_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if self.event_logger:
            self.event_logger(
                FactoryEvent(
                    timestamp=self.env.now,
                    event_type=event_type,
                    station_id=self.station_id,
                    buffer_id=self.downstream_buffer.buffer_id if self.downstream_buffer else None,
                    vehicle_id=vehicle_id,
                    cycle_time=cycle_time,
                    machine_state=self.machine_state,
                    queue_before=queue_before,
                    queue_after=queue_after,
                    buffer_before=buffer_before,
                    buffer_after=buffer_after,
                    details=details or {},
                )
            )

    def _set_state(self, new_state: MachineState):
        if self.machine_state == new_state:
            return

        now = self.env.now
        duration = now - self._last_state_change_time

        if self.machine_state == MachineState.RUNNING:
            self.total_busy_time += duration
        elif self.machine_state == MachineState.IDLE:
            self.total_idle_time += duration
        elif self.machine_state == MachineState.BLOCKED:
            self.total_blocked_time += duration
        elif self.machine_state == MachineState.STARVED:
            self.total_starved_time += duration
        elif self.machine_state in (MachineState.DOWN, MachineState.MAINTENANCE, MachineState.MICRO_STOP):
            self.total_down_time += duration

        old_state = self.machine_state
        self.machine_state = new_state
        self._last_state_change_time = now

        if new_state == MachineState.BLOCKED:
            self.blocked_count += 1
            self._log_event(EventType.BLOCKED_START, vehicle_id=self.current_vehicle.id if self.current_vehicle else None)
        elif old_state == MachineState.BLOCKED:
            self._log_event(EventType.BLOCKED_END, vehicle_id=self.current_vehicle.id if self.current_vehicle else None)

        if new_state == MachineState.STARVED:
            self.starved_count += 1
            self._log_event(EventType.STARVED_START)
        elif old_state == MachineState.STARVED:
            self._log_event(EventType.STARVED_END)

        if new_state in (MachineState.DOWN, MachineState.MAINTENANCE, MachineState.MICRO_STOP):
            self.down_count += 1
            self._log_event(EventType.DOWN_START, details={"reason": "machine_failure"})
        elif old_state in (MachineState.DOWN, MachineState.MAINTENANCE, MachineState.MICRO_STOP):
            self._log_event(EventType.DOWN_END, details={"reason": "repair_completed"})

    def _get_upstream_queue_len(self) -> int:
        if self.upstream_buffer:
            return self.upstream_buffer.current_occupancy
        if self.input_queue:
            return len(self.input_queue.items)
        return 0

    def _get_downstream_buffer_occ(self) -> Optional[int]:
        if self.downstream_buffer:
            return self.downstream_buffer.current_occupancy
        return None

    def _run_loop(self):
        """Main lifecycle of the SimPy station."""
        while True:
            # 1. Fetch next vehicle
            q_len_before = self._get_upstream_queue_len()

            if q_len_before == 0:
                self._set_state(MachineState.STARVED)
            else:
                self._set_state(MachineState.IDLE)

            if self.upstream_buffer:
                vehicle: VehicleState = yield from self.upstream_buffer.get()
            elif self.input_queue:
                vehicle: VehicleState = yield self.input_queue.get()
            else:
                break

            q_len_after = self._get_upstream_queue_len()
            buf_occ_before = self._get_downstream_buffer_occ()

            self.current_vehicle = vehicle
            vehicle.current_station_id = self.station_id
            entered_at = self.env.now

            self._set_state(MachineState.RUNNING)

            self._log_event(
                EventType.PROCESSING_START,
                vehicle_id=vehicle.id,
                queue_before=q_len_before,
                queue_after=q_len_after,
                buffer_before=buf_occ_before,
                buffer_after=buf_occ_before,
            )

            # 2. Check for breakdown/failure event during cycle
            effective_fail_prob = self.get_effective_failure_probability()
            if effective_fail_prob > 0 and self.rng.random() < effective_fail_prob:
                self._set_state(MachineState.DOWN)
                repair_time = float(max(5.0, self.rng.normal(self.config.repair_time, self.config.repair_time_std)))
                yield self.env.timeout(repair_time)
                self._set_state(MachineState.RUNNING)

            # 3. Simulate processing time with effective baseline and std
            base_ct = self.get_effective_baseline_cycle_time()
            ct_std = self.get_effective_cycle_time_std()

            if ct_std > 0:
                sampled_cycle = float(
                    max(self.config.min_cycle_time, self.rng.normal(base_ct, ct_std))
                )
            else:
                sampled_cycle = float(base_ct)

            self.last_cycle_time = sampled_cycle
            yield self.env.timeout(sampled_cycle)

            completed_at = self.env.now
            deviation = (sampled_cycle - self.config.baseline_cycle_time) / max(1.0, self.config.baseline_cycle_time)

            exposure = ExposureLevel.LOW
            if deviation > 0.20:
                exposure = ExposureLevel.HIGH
            elif deviation > 0.08:
                exposure = ExposureLevel.MEDIUM

            # Record vehicle pass history
            vehicle_pass = VehiclePass(
                station_id=self.station_id,
                entered_at=entered_at,
                completed_at=completed_at,
                actual_cycle_time=sampled_cycle,
                expected_cycle_time=self.config.baseline_cycle_time,
                torque_variance=round(float(self.rng.uniform(0.1, 0.5)), 3) if self.station_id == StationId.S3 else None,
                thermal_delta=round(float(self.rng.uniform(0.0, 1.2)), 2) if self.station_id == StationId.S2 else None,
                exposure_flag=exposure,
                deviation_at_pass=round(deviation, 3),
            )
            vehicle.history.append(vehicle_pass)
            self.total_processed += 1

            # 4. Transfer to downstream buffer or sink with finite blocking
            if self.downstream_buffer:
                buf_before_put = self.downstream_buffer.current_occupancy
                if self.downstream_buffer.is_full:
                    self._set_state(MachineState.BLOCKED)

                # Push to downstream buffer (will yield until space becomes available)
                yield from self.downstream_buffer.put(vehicle)

                buf_after_put = self.downstream_buffer.current_occupancy
                self._log_event(
                    EventType.PROCESSING_COMPLETE,
                    vehicle_id=vehicle.id,
                    cycle_time=sampled_cycle,
                    queue_before=q_len_before,
                    queue_after=q_len_after,
                    buffer_before=buf_before_put,
                    buffer_after=buf_after_put,
                )
                self.current_vehicle = None
                vehicle.current_station_id = None
            else:
                # Terminal station S6 -> mark completed and sink
                vehicle.is_completed = True
                vehicle.completed_at = self.env.now
                vehicle.total_transit_time = self.env.now - vehicle.created_at
                vehicle.current_station_id = None
                self._log_event(
                    EventType.VEHICLE_FINISHED,
                    vehicle_id=vehicle.id,
                    cycle_time=sampled_cycle,
                    queue_before=q_len_before,
                    queue_after=q_len_after,
                    details={"total_transit_time": vehicle.total_transit_time},
                )
                if self.completed_sink:
                    self.completed_sink(vehicle)
                self.current_vehicle = None

    def get_telemetry(self) -> TelemetryState:
        now = self.env.now
        current_busy = self.total_busy_time
        if self.machine_state == MachineState.RUNNING:
            current_busy += (now - self._last_state_change_time)

        utilization = (current_busy / max(1.0, now)) * 100.0 if now > 0 else 0.0
        q_len = self._get_upstream_queue_len()
        wip = q_len + (1 if self.current_vehicle is not None else 0)

        sensor = self.config.sensor_config
        vib_offset = float(self.dynamic_vibration_offset(now)) if self.dynamic_vibration_offset else 0.0
        temp_offset = float(self.dynamic_temperature_offset(now)) if self.dynamic_temperature_offset else 0.0
        curr_var_offset = float(self.dynamic_current_variance_offset(now)) if self.dynamic_current_variance_offset else 0.0

        temp_val = round(sensor.base_temperature + temp_offset + float(self.rng.normal(0, sensor.temperature_std)), 1)
        vib_val = round(max(0.1, sensor.base_vibration + vib_offset + float(self.rng.normal(0, sensor.vibration_std))), 2)
        curr_val = round(max(1.0, sensor.base_motor_current + float(self.rng.normal(0, sensor.motor_current_std))), 1)
        current_variance = round(max(0.01, sensor.base_variance + curr_var_offset), 3)

        effective_base_ct = self.get_effective_baseline_cycle_time(now)

        return TelemetryState(
            cycle_time=round(self.last_cycle_time, 1),
            baseline_cycle_time=round(effective_base_ct, 1),
            utilization=round(min(100.0, max(0.0, utilization)), 1),
            queue_length=q_len,
            buffer_max=self.upstream_buffer.capacity if self.upstream_buffer else 5,
            wip=wip,
            temperature=temp_val,
            vibration=vib_val,
            motor_current=curr_val,
            current_variance=current_variance,
            machine_state=self.machine_state,
            confidence=sensor.confidence,
            instrumentation_level=sensor.instrumentation_level,
        )

    def get_state(self) -> StationState:
        now = self.env.now
        current_busy = self.total_busy_time
        current_idle = self.total_idle_time
        current_blocked = self.total_blocked_time
        current_starved = self.total_starved_time
        current_down = self.total_down_time

        duration_in_cur = now - self._last_state_change_time
        if self.machine_state == MachineState.RUNNING:
            current_busy += duration_in_cur
        elif self.machine_state == MachineState.IDLE:
            current_idle += duration_in_cur
        elif self.machine_state == MachineState.BLOCKED:
            current_blocked += duration_in_cur
        elif self.machine_state == MachineState.STARVED:
            current_starved += duration_in_cur
        elif self.machine_state in (MachineState.DOWN, MachineState.MAINTENANCE, MachineState.MICRO_STOP):
            current_down += duration_in_cur

        telemetry = self.get_telemetry()

        return StationState(
            id=self.station_id,
            name=self.config.name,
            sub_title=self.config.sub_title,
            description=self.config.description,
            color=self.config.color,
            active_tooling=self.config.active_tooling,
            sensor_count=self.config.sensor_config.sensor_count,
            spatial_neighbors=list(self.config.spatial_neighbors),
            telemetry=telemetry,
            total_processed=self.total_processed,
            total_busy_time=round(current_busy, 2),
            total_idle_time=round(current_idle, 2),
            total_blocked_time=round(current_blocked, 2),
            total_starved_time=round(current_starved, 2),
            total_down_time=round(current_down, 2),
            blocked_count=self.blocked_count,
            starved_count=self.starved_count,
            down_count=self.down_count,
        )
