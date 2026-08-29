"""
Decision Audit Trail and Explainability Logger Module.

Records decision metadata, rule activations, input evidence hashes, and reasoning chains.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from backend.app.decision.aggregation import FactorySnapshotContext
from backend.app.decision.schemas import (
    FactoryDecision,
    RecommendedActionItem,
    RootCauseHypothesis,
)


class DecisionAuditLogger:
    """
    Builds a structured audit trail payload for every generated FactoryDecision.
    """

    def __init__(self) -> None:
        pass

    def build_audit_record(
        self,
        timestamp: float,
        context: FactorySnapshotContext,
        factory_status: str,
        overall_risk: float,
        root_causes: List[RootCauseHypothesis],
        recommended_actions: List[RecommendedActionItem],
    ) -> Dict[str, Any]:
        """
        Constructs an audit dictionary summarizing input facts and triggered reasoning rules.
        """
        return {
            "decision_timestamp": round(float(timestamp), 2),
            "engine_version": "1.0.0",
            "evaluated_stations_count": len(context.stations),
            "evaluated_vehicles_count": context.vehicle_summary.get("total_vehicles_evaluated", 0),
            "input_evidence_count": len(context.evidence_items),
            "active_anomalies": context.active_anomalies,
            "primary_bottleneck_station": context.primary_bottleneck_station,
            "overall_risk_score": overall_risk,
            "assigned_status": factory_status,
            "hypotheses_diagnosed": [rc.hypothesis_id for rc in root_causes],
            "actions_prescribed": [ra.action for ra in recommended_actions],
            "execution_timestamp": time.time(),
        }
