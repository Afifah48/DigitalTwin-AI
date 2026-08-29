"""
Factory Impact Analysis and Spatial Flow Propagation Interpreter.

Quantifies the broader system consequences on plant flow, neighboring stations,
buffers, and manufactured vehicles.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.app.decision.aggregation import FactorySnapshotContext
from backend.app.decision.schemas import ImpactSummary, PropagationDirection


class FactoryImpactAnalyzer:
    """
    Analyzes spatial flow propagation and vehicle containment requirements.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

    def analyze_impact(
        self,
        context: FactorySnapshotContext,
    ) -> ImpactSummary:
        """
        Synthesizes the station, flow, and vehicle consequences.
        """
        affected_stations: List[str] = list(context.active_anomalies)
        if context.primary_bottleneck_station and context.primary_bottleneck_station not in affected_stations:
            affected_stations.append(context.primary_bottleneck_station)

        # Collect upstream blocked and downstream starved stations
        upstream_blocked: List[str] = []
        downstream_starved: List[str] = []

        for st_id, st_ctx in context.stations.items():
            if st_ctx.upstream_blocking_risk >= 0.50 or st_ctx.machine_state == "BLOCKED":
                upstream_blocked.append(st_id)
            if st_ctx.downstream_starvation_risk >= 0.50 or st_ctx.machine_state == "STARVED":
                downstream_starved.append(st_id)

        # Determine propagation direction
        has_upstream = len(upstream_blocked) > 0
        has_downstream = len(downstream_starved) > 0

        if has_upstream and has_downstream:
            prop_dir = PropagationDirection.BIDIRECTIONAL.value
            prop_desc = (
                f"Bidirectional bottleneck propagation: Upstream stations ({', '.join(upstream_blocked)}) "
                f"face buffer saturation/blocking, while downstream stations ({', '.join(downstream_starved)}) are starving for parts."
            )
        elif has_upstream:
            prop_dir = PropagationDirection.UPSTREAM_BLOCKING.value
            prop_desc = (
                f"Upstream blocking propagation: High buffer pressure behind bottleneck station "
                f"threatens to block upstream stations ({', '.join(upstream_blocked)})."
            )
        elif has_downstream:
            prop_dir = PropagationDirection.DOWNSTREAM_STARVATION.value
            prop_desc = (
                f"Downstream starvation propagation: Bottleneck cycle delay is starving downstream stations ({', '.join(downstream_starved)})."
            )
        else:
            prop_dir = PropagationDirection.NONE.value
            prop_desc = "Nominal line flow without significant spatial buffer propagation."

        # Add propagated stations to total affected list
        all_affected = sorted(list(set(affected_stations + upstream_blocked + downstream_starved)))

        # Vehicle quality impact
        v_summary = context.vehicle_summary
        high_risk_v = context.high_risk_vehicles
        med_risk_v_count = v_summary.get("medium_risk_count", 0)

        return ImpactSummary(
            affected_stations=all_affected,
            propagation_direction=prop_dir,
            propagation_description=prop_desc,
            upstream_blocked_stations=sorted(upstream_blocked),
            downstream_starved_stations=sorted(downstream_starved),
            affected_vehicles=high_risk_v,
            high_risk_vehicle_count=len(high_risk_v),
            medium_risk_vehicle_count=med_risk_v_count,
        )
