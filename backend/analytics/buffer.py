"""
Buffer and flow dynamics analytics module.

Calculates buffer pressure, saturation events, time near saturation, running average occupancy,
as well as station blocking and starvation ratios across the manufacturing line.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BufferPressureLevel(str, Enum):
    LOW = "LOW"            # < 0.40
    NORMAL = "NORMAL"      # 0.40 - 0.75
    HIGH = "HIGH"          # 0.75 - 0.90
    CRITICAL = "CRITICAL"  # >= 0.90


@dataclass
class BufferAnalytics:
    """Detailed analytics for an inter-station buffer."""
    buffer_id: str
    occupancy: float
    capacity: float
    pressure: float  # occupancy / capacity in [0.0, 1.0+]
    pressure_level: str  # LOW, NORMAL, HIGH, CRITICAL
    time_near_saturation: float  # Total time or steps pressure was >= 0.85
    saturation_events: int  # Number of times buffer transitioned into saturation
    average_occupancy: float
    is_saturated: bool
    upstream_station: Optional[str] = None
    downstream_station: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StationFlowAnalytics:
    """Blocking and starvation flow analytics for a station."""
    station_id: str
    blocked_time: float
    starved_time: float
    observation_window: float
    blocking_rate: float  # blocked_time / observation_window [0.0, 1.0]
    starvation_rate: float  # starved_time / observation_window [0.0, 1.0]
    is_blocked: bool
    is_starved: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_buffer_pressure(occupancy: float, capacity: float) -> float:
    """
    Calculates buffer pressure:
    pressure = occupancy / capacity

    Args:
        occupancy: Current number of units in buffer.
        capacity: Maximum unit capacity of buffer.

    Returns:
        Buffer pressure ratio (clamped >= 0.0).
    """
    if occupancy is None or capacity is None or capacity <= 0 or math.isnan(occupancy):
        return 0.0
    return max(0.0, float(occupancy) / float(capacity))


def get_pressure_level(pressure: float) -> BufferPressureLevel:
    """Categorizes pressure into LOW, NORMAL, HIGH, or CRITICAL levels."""
    if pressure >= 0.90:
        return BufferPressureLevel.CRITICAL
    if pressure >= 0.75:
        return BufferPressureLevel.HIGH
    if pressure >= 0.40:
        return BufferPressureLevel.NORMAL
    return BufferPressureLevel.LOW


def calculate_blocking(blocked_time: float, observation_window: float) -> float:
    """
    Calculates station blocking ratio:
    blocking_rate = blocked_time / observation_window

    Returns:
        Blocking rate clamped to [0.0, 1.0].
    """
    if (
        blocked_time is None
        or observation_window is None
        or observation_window <= 0
        or math.isnan(blocked_time)
    ):
        return 0.0
    rate = max(0.0, float(blocked_time) / float(observation_window))
    return min(1.0, rate)


def calculate_starvation(starved_time: float, observation_window: float) -> float:
    """
    Calculates station starvation ratio:
    starvation_rate = starved_time / observation_window

    Returns:
        Starvation rate clamped to [0.0, 1.0].
    """
    if (
        starved_time is None
        or observation_window is None
        or observation_window <= 0
        or math.isnan(starved_time)
    ):
        return 0.0
    rate = max(0.0, float(starved_time) / float(observation_window))
    return min(1.0, rate)


class BufferTracker:
    """
    Tracks state, saturation duration, and running statistics for a buffer over time.
    """

    def __init__(
        self,
        buffer_id: str,
        capacity: float = 10.0,
        saturation_threshold: float = 0.85,
        upstream_station: Optional[str] = None,
        downstream_station: Optional[str] = None,
    ) -> None:
        self.buffer_id = buffer_id
        self.capacity = max(1.0, float(capacity))
        self.saturation_threshold = saturation_threshold
        self.upstream_station = upstream_station
        self.downstream_station = downstream_station

        self.occupancy_history: List[float] = []
        self.time_near_saturation: float = 0.0
        self.saturation_events: int = 0
        self._was_saturated: bool = False
        self.total_steps: int = 0

    def update(self, occupancy: float, time_step_duration: float = 1.0) -> BufferAnalytics:
        """
        Updates buffer tracker with current occupancy.

        Args:
            occupancy: Current unit occupancy in the buffer.
            time_step_duration: Duration of this observation step (default 1.0s).

        Returns:
            BufferAnalytics snapshot.
        """
        occ = max(0.0, float(occupancy) if occupancy is not None and not math.isnan(occupancy) else 0.0)
        self.occupancy_history.append(occ)
        self.total_steps += 1

        pressure = calculate_buffer_pressure(occ, self.capacity)
        is_sat = pressure >= self.saturation_threshold

        if is_sat:
            self.time_near_saturation += time_step_duration
            if not self._was_saturated:
                self.saturation_events += 1
                self._was_saturated = True
        else:
            self._was_saturated = False

        avg_occ = sum(self.occupancy_history) / len(self.occupancy_history)
        level = get_pressure_level(pressure)

        return BufferAnalytics(
            buffer_id=self.buffer_id,
            occupancy=round(occ, 2),
            capacity=round(self.capacity, 2),
            pressure=round(pressure, 4),
            pressure_level=level.value,
            time_near_saturation=round(self.time_near_saturation, 2),
            saturation_events=self.saturation_events,
            average_occupancy=round(avg_occ, 2),
            is_saturated=is_sat,
            upstream_station=self.upstream_station,
            downstream_station=self.downstream_station,
        )
