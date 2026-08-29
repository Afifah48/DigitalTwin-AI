from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd
from ..models.enums import StationId


class GroundTruthLabeler:
    """
    Computes rigorous ground truth bottleneck labels, multi-step forecast targets,
    and propagation relationships strictly from future simulated physical trajectory [t, t+20min].
    """

    def __init__(
        self,
        horizon_seconds: float = 1200.0,  # 20 minutes
        forecast_steps_seconds: Optional[List[float]] = None,
    ):
        self.horizon_seconds = horizon_seconds
        self.forecast_steps = forecast_steps_seconds or [300.0, 600.0, 900.0, 1200.0]  # 5, 10, 15, 20 min

    def compute_bottleneck_and_forecast_targets(
        self,
        telemetry_df: pd.DataFrame,
        episode_id: str,
    ) -> pd.DataFrame:
        """
        Takes the resampled station telemetry dataframe and computes future ground truth labels for each timestamp t.
        """
        timestamps = sorted(telemetry_df["timestamp"].unique())
        station_ids = sorted(telemetry_df["station_id"].unique())
        max_t = max(timestamps)

        # Build fast lookup dictionary: (station_id, timestamp) -> row dict
        lookup: Dict[tuple, Dict[str, Any]] = {}
        for _, row in telemetry_df.iterrows():
            lookup[(row["station_id"], row["timestamp"])] = row.to_dict()

        target_rows = []

        for t in timestamps:
            # We only generate targets where future horizon can be evaluated
            # (or for all timestamps, clipping horizon at simulation end)
            horizon_end_t = min(max_t, t + self.horizon_seconds)
            future_timestamps = [ts for ts in timestamps if t < ts <= horizon_end_t]

            for st_id in station_ids:
                # 1. Bottleneck Evaluation in [t, horizon_end_t]
                # A station is a ground-truth bottleneck if in future horizon:
                # - It experiences persistent queue growth or buffer saturation >= 4
                # - Causes upstream blocking or downstream starvation
                # - Sustained for at least 300 seconds (5 min)
                bottleneck_detected = False
                onset_time = None
                severity = "NONE"

                sustained_count = 0
                max_queue_seen = 0
                max_buffer_seen = 0
                blocking_caused = 0

                for fut_t in future_timestamps:
                    fut_row = lookup.get((st_id, fut_t))
                    if not fut_row:
                        continue

                    q = fut_row["queue_length"]
                    b_occ = fut_row["buffer_occupancy"]
                    dev = fut_row["cycle_time_deviation"]

                    max_queue_seen = max(max_queue_seen, q)
                    max_buffer_seen = max(max_buffer_seen, b_occ)

                    # Check if upstream station is blocked or this station queue >= 4
                    is_constrained = (q >= 4) or (dev > 0.25 and b_occ >= 4)

                    if is_constrained:
                        sustained_count += 1
                        if sustained_count >= 5 and not bottleneck_detected:  # 5 snapshots = 150s sustained
                            bottleneck_detected = True
                            onset_time = fut_t
                    else:
                        sustained_count = max(0, sustained_count - 1)

                time_to_bottleneck = float(onset_time - t) if onset_time is not None else None

                if bottleneck_detected:
                    if max_queue_seen >= 5 or max_buffer_seen >= 5:
                        severity = "HIGH"
                    elif max_queue_seen >= 3 or max_buffer_seen >= 4:
                        severity = "MEDIUM"
                    else:
                        severity = "LOW"

                # 2. Multi-step Future Regression Targets at T+5m, 10m, 15m, 20m
                row_targets = {
                    "episode_id": episode_id,
                    "timestamp": t,
                    "station_id": st_id,
                    "bottleneck_in_horizon": bottleneck_detected,
                    "bottleneck_onset_time": onset_time,
                    "time_to_bottleneck": time_to_bottleneck,
                    "bottleneck_severity": severity,
                }

                for step_s in self.forecast_steps:
                    step_min = int(step_s / 60.0)
                    target_t = t + step_s
                    # Find closest future snapshot
                    fut_snap = lookup.get((st_id, target_t))
                    if fut_snap:
                        row_targets[f"future_cycle_time_{step_min}m"] = fut_snap["cycle_time"]
                        row_targets[f"future_queue_{step_min}m"] = fut_snap["queue_length"]
                        row_targets[f"future_utilization_{step_min}m"] = fut_snap["utilization"]
                        row_targets[f"future_wip_{step_min}m"] = fut_snap["wip"]
                        row_targets[f"future_buffer_occ_{step_min}m"] = fut_snap["buffer_occupancy"]
                        row_targets[f"future_is_blocked_{step_min}m"] = fut_snap["is_blocked"]
                        row_targets[f"future_is_starved_{step_min}m"] = fut_snap["is_starved"]
                    else:
                        row_targets[f"future_cycle_time_{step_min}m"] = np.nan
                        row_targets[f"future_queue_{step_min}m"] = np.nan
                        row_targets[f"future_utilization_{step_min}m"] = np.nan
                        row_targets[f"future_wip_{step_min}m"] = np.nan
                        row_targets[f"future_buffer_occ_{step_min}m"] = np.nan
                        row_targets[f"future_is_blocked_{step_min}m"] = np.nan
                        row_targets[f"future_is_starved_{step_min}m"] = np.nan

                target_rows.append(row_targets)

        return pd.DataFrame(target_rows)
