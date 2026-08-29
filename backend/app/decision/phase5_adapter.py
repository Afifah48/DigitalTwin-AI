"""
Phase 5 Bottleneck Adapter for Phase 7 Decision Layer.

Provides clean, time-bounded access to Phase 5 bottleneck reasoning,
persistence metrics, and spatial flow propagation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from backend.analytics.health import FactoryHealth
from backend.analytics.pipeline import FactoryAnalytics


@dataclass
class StationBottleneckInfo:
    """Detailed bottleneck and flow risk metrics for an individual station."""
    station_id: str
    risk_score: float = 0.0
    is_bottleneck: bool = False
    confidence: float = 1.0
    persistence_score: float = 0.0
    upstream_blocking_risk: float = 0.0
    downstream_starvation_risk: float = 0.0
    propagation_score: float = 0.0
    affected_stations: List[str] = field(default_factory=list)


class Phase5DecisionAdapter:
    """
    Time-bounded adapter for Phase 5 bottleneck and flow dynamics results.
    """

    def __init__(self, historical_snapshots: Optional[Sequence[Union[FactoryAnalytics, Any]]] = None) -> None:
        self._snapshots: List[Dict[str, Any]] = []
        if historical_snapshots:
            self.ingest_snapshots(historical_snapshots)

    def ingest_snapshot(self, snapshot: Union[FactoryAnalytics, Dict[str, Any], Any]) -> None:
        if isinstance(snapshot, FactoryAnalytics):
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

            s_dict = {
                "timestamp": float(snapshot.timestamp),
                "predicted_bottleneck_station": fh.bottleneck_station,
                "bottleneck_risk": b_risk,
                "confidence": 1.0,
                "propagation_risk": 0.50 if snapshot.highest_buffer_pressure else 0.05,
                "station_ranking": ranking,
                "critical_stations": list(fh.critical_stations),
                "highest_buffer_pressure": snapshot.highest_buffer_pressure,
                "highest_blocking_risk": snapshot.highest_blocking_risk,
                "highest_starvation_risk": snapshot.highest_starvation_risk,
            }
        elif isinstance(snapshot, dict):
            s_dict = dict(snapshot)
        elif hasattr(snapshot, "timestamp"):
            s_dict = {
                "timestamp": float(getattr(snapshot, "timestamp", 0.0)),
                "predicted_bottleneck_station": getattr(snapshot, "predicted_bottleneck_station", None),
                "bottleneck_risk": float(getattr(snapshot, "bottleneck_risk", getattr(snapshot, "risk_score", 0.0))),
                "confidence": float(getattr(snapshot, "confidence", 1.0)),
                "propagation_risk": float(getattr(snapshot, "propagation_risk", getattr(snapshot, "propagation_score", 0.05))),
                "station_ranking": getattr(snapshot, "station_ranking", []),
                "critical_stations": getattr(snapshot, "critical_stations", []),
                "highest_buffer_pressure": getattr(snapshot, "highest_buffer_pressure", None),
            }
        else:
            raise TypeError(f"Unsupported snapshot type: {type(snapshot)}")

        self._snapshots.append(s_dict)

    def ingest_snapshots(self, snapshots: Sequence[Union[FactoryAnalytics, Any]]) -> None:
        for s in snapshots:
            self.ingest_snapshot(s)

    def get_snapshots_as_of(self, as_of_timestamp: float) -> List[Dict[str, Any]]:
        """Strictly returns snapshots on or before `as_of_timestamp`."""
        valid = [s for s in self._snapshots if float(s.get("timestamp", 0.0)) <= as_of_timestamp]
        return sorted(valid, key=lambda x: float(x.get("timestamp", 0.0)))

    def get_latest_bottleneck_state(self, as_of_timestamp: float) -> Optional[Dict[str, Any]]:
        """Returns the most recent bottleneck observation on or before `as_of_timestamp`."""
        snaps = self.get_snapshots_as_of(as_of_timestamp)
        return snaps[-1] if snaps else None

    def get_station_bottleneck_info(
        self,
        station_id: str,
        as_of_timestamp: float,
    ) -> StationBottleneckInfo:
        """Constructs consolidated Phase 5 information for a station up to `as_of_timestamp`."""
        snaps = self.get_snapshots_as_of(as_of_timestamp)
        if not snaps:
            return StationBottleneckInfo(station_id=station_id)

        latest = snaps[-1]
        is_bn = (latest.get("predicted_bottleneck_station") == station_id)
        b_risk = float(latest.get("bottleneck_risk", 0.0)) if is_bn else 0.0

        # Station score in ranking
        for rank_st, r_val in latest.get("station_ranking", []):
            if rank_st == station_id:
                b_risk = max(b_risk, float(r_val))
                break

        # Calculate historical persistence (fraction of recent snapshots where station was bottleneck)
        recent_window = snaps[-10:]
        bn_count = sum(1 for s in recent_window if s.get("predicted_bottleneck_station") == station_id)
        persistence = float(bn_count / len(recent_window)) if recent_window else 0.0

        # Flow blocking & starvation
        up_block = 0.85 if is_bn and latest.get("highest_buffer_pressure") else 0.10
        down_starve = 0.75 if is_bn and persistence > 0.3 else 0.10
        prop_score = max(up_block, down_starve) if is_bn else float(latest.get("propagation_risk", 0.05))

        affected = []
        if is_bn:
            affected.append(station_id)
            if up_block > 0.5:
                st_num = int(station_id.replace("S", ""))
                if st_num > 1:
                    affected.append(f"S{st_num - 1}")
            if down_starve > 0.5:
                st_num = int(station_id.replace("S", ""))
                if st_num < 6:
                    affected.append(f"S{st_num + 1}")

        return StationBottleneckInfo(
            station_id=station_id,
            risk_score=b_risk,
            is_bottleneck=is_bn,
            confidence=float(latest.get("confidence", 1.0)),
            persistence_score=persistence,
            upstream_blocking_risk=up_block,
            downstream_starvation_risk=down_starve,
            propagation_score=prop_score,
            affected_stations=sorted(list(set(affected))),
        )
