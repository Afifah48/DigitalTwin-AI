from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd
from ..models.enums import StationId, BufferId, MachineState, EventType
from ..simulation.engine import FactoryEngine
from ..scenarios.base import Scenario


class TelemetryResampler:
    """
    Converts asynchronous discrete-event factory simulations into regular 30-second snapshots.
    Generates causal station-level telemetry and rolling historical features strictly computed from t' <= t.
    """

    def __init__(self, step_seconds: float = 30.0):
        self.step_seconds = step_seconds

    def sample_episode_telemetry(
        self,
        engine: FactoryEngine,
        episode_id: str,
        max_time_seconds: float = 3600.0,
        scenario: Optional[Scenario] = None,
    ) -> pd.DataFrame:
        """
        Samples the simulation state at 30-second regular intervals: t = 0, 30, 60, ..., max_time_seconds.
        """
        timestamps = np.arange(0.0, max_time_seconds + self.step_seconds, self.step_seconds)
        events = engine.events
        station_ids = [StationId.S1, StationId.S2, StationId.S3, StationId.S4, StationId.S5, StationId.S6]

        rows = []
        # Pre-index events for fast causal feature computation
        proc_events_by_station: Dict[StationId, List[Any]] = {st: [] for st in station_ids}
        down_events_by_station: Dict[StationId, List[Any]] = {st: [] for st in station_ids}

        for ev in events:
            if ev.station_id in proc_events_by_station and ev.event_type == EventType.PROCESSING_COMPLETE:
                proc_events_by_station[ev.station_id].append(ev)
            if ev.station_id in down_events_by_station and ev.event_type == EventType.DOWN_START:
                down_events_by_station[ev.station_id].append(ev)

        # Buffer mapping
        station_buffer_map = {
            StationId.S1: BufferId.B12,
            StationId.S2: BufferId.B23,
            StationId.S3: BufferId.B34,
            StationId.S4: BufferId.B45,
            StationId.S5: BufferId.B56,
            StationId.S6: None,
        }

        # Track rolling history per station
        history_buffer: Dict[StationId, List[Dict[str, Any]]] = {st: [] for st in station_ids}

        for t in timestamps:
            sensor_masks = {st: scenario.get_sensor_mask(st, t) if scenario else {} for st in station_ids}

            for st_id in station_ids:
                st_sim = engine.stations[st_id]
                cfg = st_sim.config
                tel = st_sim.get_telemetry()
                buf_id = station_buffer_map[st_id]
                buf_sim = engine.buffers.get(buf_id) if buf_id else None

                # Compute point-in-time station metrics at timestamp t
                q_len = st_sim._get_upstream_queue_len()
                buf_occ = buf_sim.current_occupancy if buf_sim else 0
                buf_cap = buf_sim.capacity if buf_sim else 5
                wip = q_len + (1 if st_sim.current_vehicle else 0)

                base_ct = st_sim.get_effective_baseline_cycle_time(t)
                last_ct = st_sim.last_cycle_time
                ct_dev = round((last_ct - base_ct) / max(1.0, base_ct), 4)

                is_blocked = 1 if st_sim.machine_state == MachineState.BLOCKED else 0
                is_starved = 1 if st_sim.machine_state == MachineState.STARVED else 0
                is_down = 1 if st_sim.machine_state in (MachineState.DOWN, MachineState.MAINTENANCE, MachineState.MICRO_STOP) else 0

                # Recent completions in past 300s window (strictly <= t)
                recent_procs = [e for e in proc_events_by_station[st_id] if (t - 300.0) <= e.timestamp <= t]
                dep_rate = len(recent_procs) * (60.0 / 300.0)  # departures per min

                # Recent arrivals (for S1 from feeder, for other stations from upstream procs)
                if st_id == StationId.S1:
                    recent_arrivals = [e for e in events if e.event_type == EventType.VEHICLE_CREATED and (t - 300.0) <= e.timestamp <= t]
                else:
                    upstream_st = station_ids[station_ids.index(st_id) - 1]
                    recent_arrivals = [e for e in proc_events_by_station[upstream_st] if (t - 300.0) <= e.timestamp <= t]
                arr_rate = len(recent_arrivals) * (60.0 / 300.0)

                # Time since last failure (strictly <= t)
                past_downs = [e.timestamp for e in down_events_by_station[st_id] if e.timestamp <= t]
                time_since_failure = float(t - max(past_downs)) if past_downs else float(t)

                # Time since last anomaly (deviation > 10%)
                past_anomalies = [e.timestamp for e in proc_events_by_station[st_id] if e.timestamp <= t and e.cycle_time and (e.cycle_time - base_ct)/base_ct > 0.10]
                time_since_anomaly = float(t - max(past_anomalies)) if past_anomalies else float(t)

                # Causal trend features using past observations in history_buffer
                past_snapshots = history_buffer[st_id]
                if len(past_snapshots) >= 5:
                    q_hist = [s["queue_length"] for s in past_snapshots[-5:]]
                    q_growth_rate = float(q_hist[-1] - q_hist[0]) / max(1.0, len(q_hist))
                    ct_hist = [s["cycle_time"] for s in past_snapshots[-5:]]
                    ct_trend = float(ct_hist[-1] - ct_hist[0]) / max(1.0, len(ct_hist))
                    util_hist = [s["utilization"] for s in past_snapshots[-5:]]
                    util_trend = float(util_hist[-1] - util_hist[0]) / max(1.0, len(util_hist))
                else:
                    q_growth_rate = 0.0
                    ct_trend = 0.0
                    util_trend = 0.0

                # Sensor missingness mask
                mask = sensor_masks[st_id]
                temp_val = tel.temperature if mask.get("temperature", True) else np.nan
                vib_val = tel.vibration if mask.get("vibration", True) else np.nan
                curr_val = tel.motor_current if mask.get("motor_current", True) else np.nan
                var_val = tel.current_variance if mask.get("current_variance", True) else np.nan
                has_missing = not all(mask.values()) if mask else False

                row = {
                    "episode_id": episode_id,
                    "timestamp": round(float(t), 1),
                    "station_id": st_id.value,
                    "machine_state": st_sim.machine_state.value,
                    "cycle_time": float(last_ct),
                    "baseline_cycle_time": float(base_ct),
                    "cycle_time_deviation": float(ct_dev),
                    "utilization": float(tel.utilization),
                    "arrival_rate": round(float(arr_rate), 2),
                    "departure_rate": round(float(dep_rate), 2),
                    "arrival_departure_imbalance": round(float(arr_rate - dep_rate), 2),
                    "queue_length": int(q_len),
                    "wip": int(wip),
                    "buffer_occupancy": int(buf_occ),
                    "buffer_capacity": int(buf_cap),
                    "buffer_pressure": round(float(buf_occ / max(1, buf_cap)), 3),
                    "queue_growth_rate": round(float(q_growth_rate), 3),
                    "cycle_time_trend": round(float(ct_trend), 3),
                    "utilization_trend": round(float(util_trend), 3),
                    "time_since_last_failure": round(float(time_since_failure), 1),
                    "time_since_last_anomaly": round(float(time_since_anomaly), 1),
                    "temperature": temp_val,
                    "vibration": vib_val,
                    "motor_current": curr_val,
                    "current_variance": var_val,
                    "is_blocked": is_blocked,
                    "is_starved": is_starved,
                    "is_down": is_down,
                    "sensor_missing_flag": has_missing,
                }
                rows.append(row)
                history_buffer[st_id].append(row)

        return pd.DataFrame(rows)
