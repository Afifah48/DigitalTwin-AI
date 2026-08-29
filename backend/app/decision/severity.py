"""
Factory Severity and Overall Risk Assessment Engine.

Evaluates multi-factor industrial evidence (anomalies, bottlenecks, persistence,
propagation, and vehicle defect exposure) to compute a normalized overall risk score [0.0, 1.0]
and categorize factory health into NOMINAL, LOW, MEDIUM, HIGH, or CRITICAL.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from backend.app.decision.aggregation import FactorySnapshotContext
from backend.app.decision.schemas import FactoryStatus


class FactorySeverityEngine:
    """
    Deterministic severity assessment engine.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        sev_cfg = cfg.get("severity_thresholds", {})
        self.critical_risk_thresh = float(sev_cfg.get("critical_risk_threshold", 0.70))
        self.high_risk_thresh = float(sev_cfg.get("high_risk_threshold", 0.50))
        self.medium_risk_thresh = float(sev_cfg.get("medium_risk_threshold", 0.25))
        self.low_risk_thresh = float(sev_cfg.get("low_risk_threshold", 0.10))
        self.min_confidence_critical = float(sev_cfg.get("min_confidence_for_critical", 0.60))

    def evaluate_severity(
        self,
        context: FactorySnapshotContext,
    ) -> Tuple[str, float, float]:
        """
        Computes (factory_status, overall_risk, confidence).

        Risk Calculation Components:
        - Bottleneck Risk (Phase 5) + Persistence & Propagation: 35%
        - Station Anomaly Severities (Phase 4): 25%
        - Vehicle Quality Exposure (Phase 6): 25%
        - Physical Machine State / Downtime: 15%
        """
        # 1. Bottleneck & Flow Risk Component
        bn_risk = context.bottleneck_risk
        prop_risk = context.propagation_risk
        bn_component = max(bn_risk, 0.60 * bn_risk + 0.40 * prop_risk)

        # 2. Anomaly Component
        anomaly_scores = [ctx.anomaly_score for ctx in context.stations.values()]
        max_anom = max(anomaly_scores) if anomaly_scores else 0.0
        active_anom_count = len(context.active_anomalies)
        anom_component = min(1.0, 0.75 * max_anom + 0.25 * min(1.0, active_anom_count / 2.0))

        # 3. Vehicle Quality Risk Component
        v_summary = context.vehicle_summary
        high_v_count = v_summary.get("high_risk_count", 0)
        max_v_prob = v_summary.get("max_defect_probability", 0.0)
        v_component = min(1.0, 0.70 * max_v_prob + 0.30 * min(1.0, high_v_count / 2.0))

        # 4. Machine State Component
        states = [ctx.machine_state for ctx in context.stations.values()]
        state_score = 0.0
        if any(s in ("DOWN", "FAULT", "ERROR") for s in states):
            state_score = 0.95
        elif any(s in ("WARNING", "MAINTENANCE") for s in states):
            state_score = 0.60
        elif any(s in ("BLOCKED", "STARVED") for s in states):
            state_score = 0.40

        # Aggregate Overall Risk Score
        overall_risk = (
            0.35 * bn_component
            + 0.25 * anom_component
            + 0.25 * v_component
            + 0.15 * state_score
        )
        overall_risk = float(min(1.0, max(0.0, overall_risk)))

        # Multi-factor Confidence
        confidence = 1.0
        if active_anom_count == 0 and overall_risk > 0.40:
            confidence = 0.75

        # Check for Critical Compound Trigger (Severe anomaly + Severe Bottleneck + Quality Defect)
        is_compound_critical = (max_anom >= 0.85 and bn_risk >= 0.85 and max_v_prob >= 0.85)

        # Map to Categorical Factory Status
        if (overall_risk >= self.critical_risk_thresh and (bn_risk >= 0.70 or state_score >= 0.80 or high_v_count >= 1)) or is_compound_critical:
            status = FactoryStatus.CRITICAL.value
        elif overall_risk >= self.high_risk_thresh:
            status = FactoryStatus.HIGH.value
        elif overall_risk >= self.medium_risk_thresh:
            status = FactoryStatus.MEDIUM.value
        elif overall_risk >= self.low_risk_thresh:
            status = FactoryStatus.LOW.value
        else:
            status = FactoryStatus.NOMINAL.value

        return status, round(overall_risk, 4), round(confidence, 4)
