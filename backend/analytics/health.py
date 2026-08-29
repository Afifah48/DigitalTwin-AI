"""
Station and factory health calculation module.

Combines telemetry deviation, buffer pressure, blocking/starvation rates, machine state,
and sensor confidence into comprehensive health scores (0.0 - 100.0) and status classifications
(NOMINAL, WATCH, DEGRADED, CRITICAL).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union


class HealthLevel(str, Enum):
    NOMINAL = "NOMINAL"    # Score >= 85.0
    WATCH = "WATCH"        # 70.0 <= Score < 85.0
    DEGRADED = "DEGRADED"  # 45.0 <= Score < 70.0
    CRITICAL = "CRITICAL"  # Score < 45.0


# State penalties deducted from the 100-point base health score
DEFAULT_STATE_PENALTIES: Dict[str, float] = {
    "RUNNING": 0.0,
    "IDLE": 5.0,
    "BLOCKED": 15.0,
    "STARVED": 15.0,
    "WARNING": 20.0,
    "SETUP": 10.0,
    "MAINTENANCE": 35.0,
    "FAULT": 60.0,
    "DOWN": 60.0,
    "ERROR": 60.0,
    "OFFLINE": 80.0,
    "UNKNOWN": 10.0,
}

# Penalty weights for continuous factors (scaled against 100 base points)
DEFAULT_HEALTH_WEIGHTS = {
    "deviation": 35.0,     # Max 35 point deduction for deviation = 1.0
    "buffer": 15.0,        # Max 15 point deduction for buffer pressure = 1.0
    "flow": 20.0,          # Max 20 point deduction for blocking / starvation = 1.0
    "state_cap": 60.0,     # Max point deduction for discrete state
}


@dataclass
class MachineHealthBreakdown:
    """Detailed breakdown of constituent scores and penalties for machine health."""
    base_score: float = 100.0
    deviation_penalty: float = 0.0
    buffer_penalty: float = 0.0
    flow_penalty: float = 0.0
    state_penalty: float = 0.0
    confidence_penalty: float = 0.0
    machine_state: str = "RUNNING"
    telemetry_confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StationHealth:
    """Consolidated health report for an individual station."""
    station_id: str
    health_score: float  # [0.0, 100.0]
    health_level: str    # NOMINAL, WATCH, DEGRADED, CRITICAL
    machine_health: MachineHealthBreakdown
    is_healthy: bool     # True if NOMINAL or WATCH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "station_id": self.station_id,
            "health_score": self.health_score,
            "health_level": self.health_level,
            "is_healthy": self.is_healthy,
            "machine_health": self.machine_health.to_dict(),
        }


@dataclass
class FactoryHealth:
    """Overall factory-level health score and line-wide alarm summary."""
    health_score: float  # [0.0, 100.0]
    health_level: str    # NOMINAL, WATCH, DEGRADED, CRITICAL
    station_scores: Dict[str, float] = field(default_factory=dict)
    bottleneck_station: Optional[str] = None
    critical_stations: List[str] = field(default_factory=list)
    degraded_stations: List[str] = field(default_factory=list)
    watch_stations: List[str] = field(default_factory=list)
    nominal_stations: List[str] = field(default_factory=list)
    active_alarms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def score_to_health_level(score: float) -> HealthLevel:
    """Maps a 0.0-100.0 health score to a categorical HealthLevel."""
    if score >= 85.0:
        return HealthLevel.NOMINAL
    elif score >= 70.0:
        return HealthLevel.WATCH
    elif score >= 45.0:
        return HealthLevel.DEGRADED
    else:
        return HealthLevel.CRITICAL


def calculate_station_health(
    station_id: str,
    deviation_score: float = 0.0,
    buffer_pressure: float = 0.0,
    blocking_rate: float = 0.0,
    starvation_rate: float = 0.0,
    machine_state: str = "RUNNING",
    telemetry_confidence: float = 1.0,
    weights: Optional[Dict[str, float]] = None,
) -> StationHealth:
    """
    Computes a station's health score by deducting weighted penalties from a 100.0 base.

    Args:
        station_id: Identifier of the station (e.g. 'S1').
        deviation_score: Normalized telemetry deviation in [0.0, 1.0].
        buffer_pressure: Immediate buffer pressure ratio in [0.0, 1.0+].
        blocking_rate: Ratio of time blocked in observation window in [0.0, 1.0].
        starvation_rate: Ratio of time starved in observation window in [0.0, 1.0].
        machine_state: Current operational state (RUNNING, IDLE, BLOCKED, FAULT, etc.).
        telemetry_confidence: Confidence in the sensor data in [0.0, 1.0].
        weights: Optional penalty weight dictionary.

    Returns:
        StationHealth containing health_score, health_level, and breakdown.
    """
    cfg_weights = dict(DEFAULT_HEALTH_WEIGHTS)
    if weights:
        cfg_weights.update(weights)

    norm_dev = max(0.0, min(1.0, float(deviation_score) if deviation_score is not None else 0.0))
    norm_buf = max(0.0, min(1.0, float(buffer_pressure) if buffer_pressure is not None else 0.0))
    norm_block = max(0.0, min(1.0, float(blocking_rate) if blocking_rate is not None else 0.0))
    norm_starve = max(0.0, min(1.0, float(starvation_rate) if starvation_rate is not None else 0.0))
    norm_conf = max(0.0, min(1.0, float(telemetry_confidence) if telemetry_confidence is not None else 1.0))

    state_str = str(machine_state or "RUNNING").upper().strip()

    # Penalties
    dev_penalty = norm_dev * cfg_weights.get("deviation", 35.0)
    buf_penalty = norm_buf * cfg_weights.get("buffer", 15.0)
    
    # Combined flow penalty (blocking + starvation)
    flow_severity = max(norm_block, norm_starve) * 0.7 + min(norm_block, norm_starve) * 0.3
    flow_penalty = flow_severity * cfg_weights.get("flow", 20.0)

    # State penalty
    state_penalty = DEFAULT_STATE_PENALTIES.get(state_str, 10.0)

    # Telemetry confidence penalty (deducts up to 10 points if sensors are untrustworthy)
    conf_penalty = (1.0 - norm_conf) * 10.0

    total_deductions = dev_penalty + buf_penalty + flow_penalty + state_penalty + conf_penalty
    raw_score = max(0.0, min(100.0, 100.0 - total_deductions))
    final_score = round(raw_score, 2)

    level = score_to_health_level(final_score)
    is_healthy = level in (HealthLevel.NOMINAL, HealthLevel.WATCH)

    breakdown = MachineHealthBreakdown(
        base_score=100.0,
        deviation_penalty=round(dev_penalty, 2),
        buffer_penalty=round(buf_penalty, 2),
        flow_penalty=round(flow_penalty, 2),
        state_penalty=round(state_penalty, 2),
        confidence_penalty=round(conf_penalty, 2),
        machine_state=state_str,
        telemetry_confidence=round(norm_conf, 4),
    )

    return StationHealth(
        station_id=station_id,
        health_score=final_score,
        health_level=level.value,
        machine_health=breakdown,
        is_healthy=is_healthy,
    )


def calculate_factory_health(
    station_healths: Union[List[StationHealth], Dict[str, StationHealth]],
    buffer_pressures: Optional[Dict[str, float]] = None,
    station_criticality: Optional[Dict[str, float]] = None,
) -> FactoryHealth:
    """
    Combines individual station health reports and buffer dynamics into factory-wide health.

    Applies bottleneck weighting: the weakest critical station significantly influences
    factory overall health (harmonic/weighted average).

    Args:
        station_healths: List or dictionary of StationHealth instances.
        buffer_pressures: Optional dictionary of buffer ID -> pressure.
        station_criticality: Optional dictionary mapping station_id -> importance weight.

    Returns:
        FactoryHealth snapshot.
    """
    if isinstance(station_healths, dict):
        stations_list = list(station_healths.values())
    else:
        stations_list = list(station_healths)

    if not stations_list:
        return FactoryHealth(
            health_score=100.0,
            health_level=HealthLevel.NOMINAL.value,
        )

    station_scores: Dict[str, float] = {}
    critical_st: List[str] = []
    degraded_st: List[str] = []
    watch_st: List[str] = []
    nominal_st: List[str] = []
    active_alarms: List[str] = []

    lowest_score = 100.0
    bottleneck_station: Optional[str] = None

    total_weighted_score = 0.0
    total_weights = 0.0

    for st in stations_list:
        score = st.health_score
        st_id = st.station_id
        station_scores[st_id] = score

        if score < lowest_score:
            lowest_score = score
            bottleneck_station = st_id

        # Categorize
        if st.health_level == HealthLevel.CRITICAL.value:
            critical_st.append(st_id)
            active_alarms.append(f"Station {st_id} is in CRITICAL condition (Score: {score})")
        elif st.health_level == HealthLevel.DEGRADED.value:
            degraded_st.append(st_id)
            active_alarms.append(f"Station {st_id} is DEGRADED (Score: {score})")
        elif st.health_level == HealthLevel.WATCH.value:
            watch_st.append(st_id)
        else:
            nominal_st.append(st_id)

        # Importance weight
        w = 1.0
        if station_criticality and st_id in station_criticality:
            w = max(0.1, station_criticality[st_id])

        total_weighted_score += score * w
        total_weights += w

    # Line-level score is 60% weighted average + 40% bottleneck lowest score
    weighted_avg = total_weighted_score / total_weights if total_weights > 0 else lowest_score
    factory_raw = (0.60 * weighted_avg) + (0.40 * lowest_score)

    # Apply buffer pressure penalty across line if buffers are saturated
    if buffer_pressures:
        max_buf = max(buffer_pressures.values()) if buffer_pressures else 0.0
        if max_buf >= 0.90:
            factory_raw -= 10.0
            active_alarms.append(f"High Buffer Saturation detected (Max Pressure: {max_buf:.2f})")
        elif max_buf >= 0.75:
            factory_raw -= 5.0

    factory_final = max(0.0, min(100.0, round(factory_raw, 2)))
    fac_level = score_to_health_level(factory_final)

    return FactoryHealth(
        health_score=factory_final,
        health_level=fac_level.value,
        station_scores=station_scores,
        bottleneck_station=bottleneck_station,
        critical_stations=critical_st,
        degraded_stations=degraded_st,
        watch_stations=watch_st,
        nominal_stations=nominal_st,
        active_alarms=active_alarms,
    )
