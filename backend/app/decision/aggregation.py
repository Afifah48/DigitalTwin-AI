"""
Factory-wide Evidence and Context Aggregation Module.

Combines telemetry snapshots, Phase 4 anomalies, Phase 5 bottlenecks, and Phase 6 vehicle
predictions into a single, cohesive, time-bounded factory context snapshot at timestamp `t`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from backend.app.decision.phase4_adapter import Phase4DecisionAdapter
from backend.app.decision.phase5_adapter import Phase5DecisionAdapter, StationBottleneckInfo
from backend.app.decision.phase6_adapter import Phase6DecisionAdapter
from backend.app.decision.schemas import DecisionEvidenceItem
from backend.quality.temporal import filter_by_timestamp


@dataclass
class StationOperationalContext:
    """Aggregated operational telemetry and multi-phase intelligence for a single station."""
    station_id: str
    timestamp: float
    # Telemetry
    cycle_time: float = 50.0
    cycle_time_delta: float = 0.0
    vibration: float = 0.09
    temperature: float = 62.0
    motor_current: float = 4.8
    current_variance: float = 0.05
    machine_state: str = "RUNNING"
    buffer_occupancy: float = 3.0
    # Phase 4 Anomaly
    is_anomalous: bool = False
    anomaly_score: float = 0.0
    anomaly_severity: str = "LOW"
    anomaly_top_signals: List[str] = field(default_factory=list)
    # Phase 5 Bottleneck
    is_bottleneck: bool = False
    bottleneck_risk: float = 0.0
    bottleneck_persistence: float = 0.0
    upstream_blocking_risk: float = 0.0
    downstream_starvation_risk: float = 0.0
    propagation_score: float = 0.0
    affected_stations: List[str] = field(default_factory=list)


@dataclass
class FactorySnapshotContext:
    """Consolidated factory state and evidence across all 6 stations at timestamp `t`."""
    timestamp: float
    stations: Dict[str, StationOperationalContext] = field(default_factory=dict)
    active_anomalies: List[str] = field(default_factory=list)
    primary_bottleneck_station: Optional[str] = None
    bottleneck_risk: float = 0.0
    propagation_risk: float = 0.0
    vehicle_summary: Dict[str, Any] = field(default_factory=dict)
    high_risk_vehicles: List[str] = field(default_factory=list)
    evidence_items: List[DecisionEvidenceItem] = field(default_factory=list)


class FactoryEvidenceAggregator:
    """
    Builds a time-bounded FactorySnapshotContext by integrating telemetry and Phase 4-6 adapters.
    """

    def __init__(
        self,
        phase4_adapter: Optional[Phase4DecisionAdapter] = None,
        phase5_adapter: Optional[Phase5DecisionAdapter] = None,
        phase6_adapter: Optional[Phase6DecisionAdapter] = None,
        station_topology: Optional[List[str]] = None,
    ) -> None:
        self.phase4 = phase4_adapter or Phase4DecisionAdapter()
        self.phase5 = phase5_adapter or Phase5DecisionAdapter()
        self.phase6 = phase6_adapter or Phase6DecisionAdapter()
        self.station_topology = station_topology or ["S1", "S2", "S3", "S4", "S5", "S6"]

    def aggregate_context(
        self,
        as_of_timestamp: float,
        telemetry_snapshots: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> FactorySnapshotContext:
        """
        Gathers all facts up to `as_of_timestamp` and produces the consolidated factory context.
        """
        as_of = float(as_of_timestamp)

        # 1. Retrieve latest telemetry up to as_of
        latest_telemetry: Dict[str, Any] = {}
        if telemetry_snapshots:
            valid_snaps = filter_by_timestamp(telemetry_snapshots, as_of)
            if valid_snaps:
                latest_telemetry = valid_snaps[-1]

        raw_stations = latest_telemetry.get("stations", {})
        raw_buffers = latest_telemetry.get("buffers", {})

        # 2. Query Adapters (strictly <= as_of)
        p4_map = self.phase4.get_latest_station_predictions(as_of)
        p5_latest = self.phase5.get_latest_bottleneck_state(as_of) or {}
        v_summary = self.phase6.get_vehicle_risk_summary(as_of)

        station_contexts: Dict[str, StationOperationalContext] = {}
        active_anomalies: List[str] = []
        evidence_list: List[DecisionEvidenceItem] = []

        primary_bn = p5_latest.get("predicted_bottleneck_station")
        max_bn_risk = float(p5_latest.get("bottleneck_risk", 0.0))
        max_prop_risk = float(p5_latest.get("propagation_risk", 0.0))

        # 3. Aggregate each station across topology
        for st_id in self.station_topology:
            st_raw = raw_stations.get(st_id, {})
            # Phase 4 Anomaly
            p4_pred = p4_map.get(st_id)
            is_anom = p4_pred.detected if p4_pred else False
            anom_score = p4_pred.anomaly_score if p4_pred else 0.0
            anom_sev = p4_pred.severity if p4_pred else "LOW"
            top_sigs = p4_pred.top_signals if p4_pred else []

            if is_anom:
                active_anomalies.append(st_id)
                evidence_list.append(
                    DecisionEvidenceItem(
                        signal=f"Phase 4 Anomaly ({', '.join(top_sigs) if top_sigs else 'Multi-channel'})",
                        value=anom_score,
                        source="Phase 4 Anomaly",
                        direction="ELEVATED",
                        strength=min(1.0, anom_score),
                        station_id=st_id,
                    )
                )

            # Phase 5 Bottleneck
            p5_info: StationBottleneckInfo = self.phase5.get_station_bottleneck_info(st_id, as_of)
            if p5_info.is_bottleneck:
                evidence_list.append(
                    DecisionEvidenceItem(
                        signal="Phase 5 Primary Bottleneck Restriction",
                        value=p5_info.risk_score,
                        source="Phase 5 Bottleneck",
                        direction="ELEVATED",
                        strength=p5_info.risk_score,
                        station_id=st_id,
                    )
                )
            if p5_info.upstream_blocking_risk >= 0.60:
                evidence_list.append(
                    DecisionEvidenceItem(
                        signal="Upstream Buffer Pressure & Blocking Risk",
                        value=p5_info.upstream_blocking_risk,
                        source="Phase 5 Bottleneck",
                        direction="SATURATED",
                        strength=p5_info.upstream_blocking_risk,
                        station_id=st_id,
                    )
                )
            if p5_info.downstream_starvation_risk >= 0.60:
                evidence_list.append(
                    DecisionEvidenceItem(
                        signal="Downstream Station Starvation Risk",
                        value=p5_info.downstream_starvation_risk,
                        source="Phase 5 Bottleneck",
                        direction="DEPLETED",
                        strength=p5_info.downstream_starvation_risk,
                        station_id=st_id,
                    )
                )

            # Associated buffer
            buf_key = f"B{st_id.replace('S', '')}"
            buf_data = raw_buffers.get(buf_key, {})
            buf_occ = float(st_raw.get("buffer_occupancy", buf_data.get("occupancy", 3.0)) or 3.0)

            # Sensor physical checks for evidence
            vib = float(st_raw.get("vibration", 0.09) or 0.09)
            if vib >= 0.25:
                evidence_list.append(
                    DecisionEvidenceItem(
                        signal="Vibration Amplitude",
                        value=vib,
                        source="Telemetry",
                        direction="ELEVATED",
                        strength=min(1.0, vib / 0.50),
                        station_id=st_id,
                    )
                )

            ct_delta = float(st_raw.get("cycle_time_delta", 0.0) or 0.0)
            if ct_delta >= 8.0:
                evidence_list.append(
                    DecisionEvidenceItem(
                        signal="Cycle Time Deviation (+s)",
                        value=ct_delta,
                        source="Telemetry",
                        direction="DEGRADED",
                        strength=min(1.0, ct_delta / 20.0),
                        station_id=st_id,
                    )
                )

            st_ctx = StationOperationalContext(
                station_id=st_id,
                timestamp=as_of,
                cycle_time=float(st_raw.get("cycle_time", 50.0) or 50.0),
                cycle_time_delta=ct_delta,
                vibration=vib,
                temperature=float(st_raw.get("temperature", 62.0) or 62.0),
                motor_current=float(st_raw.get("motor_current", 4.8) or 4.8),
                current_variance=float(st_raw.get("current_variance", 0.05) or 0.05),
                machine_state=str(st_raw.get("machine_state", st_raw.get("state", "RUNNING"))).upper(),
                buffer_occupancy=buf_occ,
                is_anomalous=is_anom,
                anomaly_score=anom_score,
                anomaly_severity=anom_sev,
                anomaly_top_signals=top_sigs,
                is_bottleneck=p5_info.is_bottleneck,
                bottleneck_risk=p5_info.risk_score,
                bottleneck_persistence=p5_info.persistence_score,
                upstream_blocking_risk=p5_info.upstream_blocking_risk,
                downstream_starvation_risk=p5_info.downstream_starvation_risk,
                propagation_score=p5_info.propagation_score,
                affected_stations=p5_info.affected_stations,
            )
            station_contexts[st_id] = st_ctx

        # 4. Phase 6 Vehicle Evidence
        high_v_ids = v_summary.get("high_risk_vehicle_ids", [])
        if high_v_ids:
            evidence_list.append(
                DecisionEvidenceItem(
                    signal=f"High-Risk Vehicle Quality Exposure (Count: {len(high_v_ids)})",
                    value=len(high_v_ids),
                    source="Phase 6 Quality",
                    direction="ELEVATED",
                    strength=min(1.0, len(high_v_ids) / 5.0),
                    station_id=primary_bn,
                )
            )

        return FactorySnapshotContext(
            timestamp=as_of,
            stations=station_contexts,
            active_anomalies=sorted(active_anomalies),
            primary_bottleneck_station=primary_bn,
            bottleneck_risk=max_bn_risk,
            propagation_risk=max_prop_risk,
            vehicle_summary=v_summary,
            high_risk_vehicles=sorted(high_v_ids),
            evidence_items=evidence_list,
        )
