"""
Operational Recommendation Engine for Factory Floor Action.

Generates deterministic, prioritized, and targeted operational actions
(e.g., machine inspection, QA containment, flow rebalancing, escalation).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.app.decision.aggregation import FactorySnapshotContext
from backend.app.decision.schemas import (
    ActionPriority,
    ActionType,
    ImpactSummary,
    RecommendedActionItem,
    RootCauseHypothesis,
)


class FactoryRecommendationEngine:
    """
    Deterministic operational policy and action engine.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

    def generate_recommendations(
        self,
        context: FactorySnapshotContext,
        root_causes: List[RootCauseHypothesis],
        impact: ImpactSummary,
        factory_status: str,
    ) -> List[RecommendedActionItem]:
        """
        Synthesizes operational recommendations based on diagnosed root causes,
        flow impact, and vehicle containment requirements.
        """
        actions: List[RecommendedActionItem] = []

        # 1. Critical Escalation if Factory is CRITICAL or Down
        if factory_status == "CRITICAL":
            actions.append(
                RecommendedActionItem(
                    action=ActionType.ESCALATE.value,
                    priority=ActionPriority.CRITICAL.value,
                    target="Plant Operations & Maintenance Leadership",
                    reason="Critical multi-station bottleneck and quality risk detected; immediate cross-functional intervention required.",
                    evidence_summary=[f"Factory Status: {factory_status}", f"Active Bottleneck: {context.primary_bottleneck_station}"],
                )
            )

        # 2. Station-Specific Machine Inspection / Repair
        for rc in root_causes:
            if rc.category == "SUDDEN_TOOL_BREAKDOWN" and rc.station_id:
                actions.append(
                    RecommendedActionItem(
                        action=ActionType.INSPECT_MACHINE.value,
                        priority=ActionPriority.CRITICAL.value,
                        target=f"Station {rc.station_id}",
                        reason=f"Emergency maintenance dispatch to clear tool jam / mechanical failure at Station {rc.station_id}.",
                        evidence_summary=[e.signal for e in rc.supporting_evidence],
                    )
                )
            elif rc.category == "MECHANICAL_DEGRADATION" and rc.station_id:
                actions.append(
                    RecommendedActionItem(
                        action=ActionType.INSPECT_MACHINE.value,
                        priority=ActionPriority.HIGH.value,
                        target=f"Station {rc.station_id}",
                        reason=f"Schedule bearing/spindle mechanical inspection and lubrication service on Station {rc.station_id} before catastrophic failure.",
                        evidence_summary=[e.signal for e in rc.supporting_evidence],
                    )
                )
            elif rc.category == "WELDING_ALIGNMENT_JITTER" and rc.station_id:
                actions.append(
                    RecommendedActionItem(
                        action=ActionType.INVESTIGATE_STATION.value,
                        priority=ActionPriority.MEDIUM.value,
                        target=f"Station {rc.station_id}",
                        reason=f"Inspect clamp fixtures and weld tip calibration on Station {rc.station_id} to eliminate vibration jitter.",
                        evidence_summary=[e.signal for e in rc.supporting_evidence],
                    )
                )

        # 3. Vehicle Quality Containment (QA Inspection)
        if impact.high_risk_vehicle_count > 0:
            v_list_str = ", ".join(impact.affected_vehicles[:5])
            if len(impact.affected_vehicles) > 5:
                v_list_str += f" (+{len(impact.affected_vehicles) - 5} more)"

            actions.append(
                RecommendedActionItem(
                    action=ActionType.QA_INSPECTION.value,
                    priority=ActionPriority.HIGH.value,
                    target=f"Vehicles [{v_list_str}]",
                    reason=f"Hold {impact.high_risk_vehicle_count} high-risk vehicles for physical QA audit, teardown, and torque verification.",
                    evidence_summary=[f"{impact.high_risk_vehicle_count} vehicles processed during station anomaly"],
                )
            )

        # 4. Flow & Buffer Balancing Actions
        if impact.upstream_blocked_stations:
            actions.append(
                RecommendedActionItem(
                    action=ActionType.CHECK_UPSTREAM_FLOW.value,
                    priority=ActionPriority.MEDIUM.value,
                    target=f"Buffers upstream of {', '.join(impact.upstream_blocked_stations)}",
                    reason="Buffer near capacity; pace upstream line intake to avoid cascading station blocking.",
                    evidence_summary=[f"Upstream blocked stations: {', '.join(impact.upstream_blocked_stations)}"],
                )
            )

        if impact.downstream_starved_stations:
            actions.append(
                RecommendedActionItem(
                    action=ActionType.CHECK_DOWNSTREAM_STARVATION.value,
                    priority=ActionPriority.MEDIUM.value,
                    target=f"Stations {', '.join(impact.downstream_starved_stations)}",
                    reason="Downstream starvation detected; rebalance cycle times and verify intermediate buffer flow.",
                    evidence_summary=[f"Starved stations: {', '.join(impact.downstream_starved_stations)}"],
                )
            )

        # 5. Default Nominal Action if no alarms
        if not actions:
            actions.append(
                RecommendedActionItem(
                    action=ActionType.MONITOR.value,
                    priority=ActionPriority.LOW.value,
                    target="Plant Line Overview",
                    reason="All stations, buffers, and vehicle quality metrics are operating within nominal parameters.",
                    evidence_summary=["All telemetry within baseline statistical bounds"],
                )
            )

        # Sort actions deterministically by priority: CRITICAL -> HIGH -> MEDIUM -> LOW
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        return sorted(actions, key=lambda a: priority_order.get(a.priority, 99))
