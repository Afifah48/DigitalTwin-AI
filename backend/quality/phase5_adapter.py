"""
Phase 5 Bottleneck Detection Adapter for Phase 6 Quality Prediction.

Provides clean, time-aware access to Phase 5 bottleneck and flow dynamics
outputs without duplicating internal graph/temporal ranking logic or leaking future data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from backend.analytics.health import FactoryHealth
from backend.analytics.pipeline import FactoryAnalytics


@dataclass
class BottleneckSnapshot:
    """A single time-indexed Phase 5 bottleneck prediction payload."""
    timestamp: float
    predicted_bottleneck_station: Optional[str] = None
    bottleneck_risk: float = 0.0          # [0.0, 1.0] continuous risk score
    confidence: float = 1.0               # [0.0, 1.0] confidence score
    propagation_risk: float = 0.0        # [0.0, 1.0] upstream/downstream risk
    station_ranking: List[Tuple[str, float]] = field(default_factory=list)
    critical_stations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Phase5Adapter:
    """
    Time-aware adapter consuming Phase 5 Bottleneck Detection outputs.

    Exposes bottleneck state, propagation risk, and station risk rankings strictly
    constrained to `timestamp <= as_of_timestamp`.
    """

    def __init__(self, historical_snapshots: Optional[Sequence[Union[BottleneckSnapshot, FactoryAnalytics, Dict[str, Any]]]] = None) -> None:
        self._snapshots: List[BottleneckSnapshot] = []
        if historical_snapshots:
            self.ingest_snapshots(historical_snapshots)

    def ingest_snapshot(self, snapshot: Union[BottleneckSnapshot, FactoryAnalytics, Dict[str, Any]]) -> None:
        """Ingests a single bottleneck observation."""
        if isinstance(snapshot, BottleneckSnapshot):
            s = snapshot
        elif isinstance(snapshot, FactoryAnalytics):
            # Extract from FactoryAnalytics pipeline output
            fh = snapshot.factory_health
            b_risk = 0.0
            if fh.health_level == "CRITICAL":
                b_risk = 0.90
            elif fh.health_level == "DEGRADED":
                b_risk = 0.65
            elif fh.health_level == "WATCH":
                b_risk = 0.35

            ranking: List[Tuple[str, float]] = []
            if fh.station_scores:
                for st_id, sc in sorted(fh.station_scores.items(), key=lambda x: x[1]):
                    ranking.append((st_id, max(0.0, round((100.0 - sc) / 100.0, 4))))

            s = BottleneckSnapshot(
                timestamp=float(snapshot.timestamp),
                predicted_bottleneck_station=fh.bottleneck_station,
                bottleneck_risk=b_risk,
                confidence=1.0,
                propagation_risk=0.5 if snapshot.highest_buffer_pressure else 0.1,
                station_ranking=ranking,
                critical_stations=list(fh.critical_stations),
            )
        elif isinstance(snapshot, dict):
            s = BottleneckSnapshot(
                timestamp=float(snapshot.get("timestamp", 0.0)),
                predicted_bottleneck_station=snapshot.get("predicted_bottleneck_station"),
                bottleneck_risk=float(snapshot.get("bottleneck_risk", 0.0)),
                confidence=float(snapshot.get("confidence", 1.0)),
                propagation_risk=float(snapshot.get("propagation_risk", 0.0)),
                station_ranking=list(snapshot.get("station_ranking", [])),
                critical_stations=list(snapshot.get("critical_stations", [])),
                metadata=dict(snapshot.get("metadata", {})),
            )
        else:
            raise TypeError(f"Unsupported snapshot type: {type(snapshot)}")

        self._snapshots.append(s)

    def ingest_snapshots(self, snapshots: Sequence[Union[BottleneckSnapshot, FactoryAnalytics, Dict[str, Any]]]) -> None:
        """Batch ingests multiple Phase 5 snapshots."""
        for s in snapshots:
            self.ingest_snapshot(s)

    def get_snapshots_as_of(self, as_of_timestamp: float) -> List[BottleneckSnapshot]:
        """
        Returns all bottleneck snapshots strictly on or before `as_of_timestamp`.
        Future data (timestamp > as_of_timestamp) is strictly excluded.
        """
        valid = [s for s in self._snapshots if s.timestamp <= as_of_timestamp]
        return sorted(valid, key=lambda x: x.timestamp)

    def get_latest_bottleneck_state(self, as_of_timestamp: float) -> Optional[BottleneckSnapshot]:
        """Returns the most recent bottleneck observation on or before `as_of_timestamp`."""
        snapshots = self.get_snapshots_as_of(as_of_timestamp)
        return snapshots[-1] if snapshots else None

    def get_station_bottleneck_exposure(
        self,
        station_id: str,
        as_of_timestamp: float,
    ) -> Dict[str, float]:
        """
        Calculates historical bottleneck exposure metrics for a specific station up to `as_of_timestamp`.
        """
        snapshots = self.get_snapshots_as_of(as_of_timestamp)
        if not snapshots:
            return {
                "station_bottleneck_frequency": 0.0,
                "mean_bottleneck_risk": 0.0,
                "max_bottleneck_risk": 0.0,
                "max_propagation_risk": 0.0,
            }

        risks: List[float] = []
        is_bottleneck_flags: List[int] = []
        prop_risks: List[float] = []

        for s in snapshots:
            is_bn = 1 if s.predicted_bottleneck_station == station_id else 0
            is_bottleneck_flags.append(is_bn)
            prop_risks.append(s.propagation_risk)

            # Find station risk in ranking
            st_risk = 0.0
            for rank_st, r_score in s.station_ranking:
                if rank_st == station_id:
                    st_risk = r_score
                    break
            if st_risk == 0.0 and is_bn:
                st_risk = s.bottleneck_risk
            risks.append(st_risk)

        return {
            "station_bottleneck_frequency": float(sum(is_bottleneck_flags) / len(is_bottleneck_flags)),
            "mean_bottleneck_risk": float(sum(risks) / len(risks)) if risks else 0.0,
            "max_bottleneck_risk": float(max(risks)) if risks else 0.0,
            "max_propagation_risk": float(max(prop_risks)) if prop_risks else 0.0,
        }
