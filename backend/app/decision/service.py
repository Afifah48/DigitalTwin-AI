"""
Decision Service Orchestrator for Factory Intelligence.

Coordinates all Phase 7 submodules to produce an end-to-end, zero-leakage,
interpretable FactoryDecision at timestamp `t`.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence, Union

from backend.app.decision.aggregation import FactoryEvidenceAggregator, FactorySnapshotContext
from backend.app.decision.audit import DecisionAuditLogger
from backend.app.decision.impact import FactoryImpactAnalyzer
from backend.app.decision.phase4_adapter import Phase4DecisionAdapter
from backend.app.decision.phase5_adapter import Phase5DecisionAdapter
from backend.app.decision.phase6_adapter import Phase6DecisionAdapter
from backend.app.decision.recommendations import FactoryRecommendationEngine
from backend.app.decision.root_cause import FactoryRootCauseEngine
from backend.app.decision.schemas import (
    FactoryDecision,
    ImpactSummary,
    RecommendedActionItem,
    RootCauseHypothesis,
)
from backend.app.decision.severity import FactorySeverityEngine

DEFAULT_CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "models", "decision", "config.json")
)


class DecisionService:
    """
    Unified Operational Intelligence & Decision Service.
    """

    def __init__(
        self,
        phase4_adapter: Optional[Phase4DecisionAdapter] = None,
        phase5_adapter: Optional[Phase5DecisionAdapter] = None,
        phase6_adapter: Optional[Phase6DecisionAdapter] = None,
        config: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
    ) -> None:
        self.phase4 = phase4_adapter or Phase4DecisionAdapter()
        self.phase5 = phase5_adapter or Phase5DecisionAdapter()
        self.phase6 = phase6_adapter or Phase6DecisionAdapter()

        # Load Configuration
        self.config: Dict[str, Any] = {}
        target_cfg_path = config_path or DEFAULT_CONFIG_PATH
        if os.path.exists(target_cfg_path):
            with open(target_cfg_path, "r") as f:
                self.config = json.load(f)
        if config:
            self.config.update(config)

        # Initialize Sub-Engines
        self.aggregator = FactoryEvidenceAggregator(
            phase4_adapter=self.phase4,
            phase5_adapter=self.phase5,
            phase6_adapter=self.phase6,
        )
        self.severity_engine = FactorySeverityEngine(self.config)
        self.root_cause_engine = FactoryRootCauseEngine(self.config)
        self.impact_analyzer = FactoryImpactAnalyzer(self.config)
        self.recommendation_engine = FactoryRecommendationEngine(self.config)
        self.audit_logger = DecisionAuditLogger()

    def analyze(
        self,
        timestamp: float,
        telemetry_snapshots: Optional[Sequence[Dict[str, Any]]] = None,
        phase4_adapter: Optional[Phase4DecisionAdapter] = None,
        phase5_adapter: Optional[Phase5DecisionAdapter] = None,
        phase6_adapter: Optional[Phase6DecisionAdapter] = None,
    ) -> FactoryDecision:
        """
        Executes factory intelligence analysis at timestamp `t`.

        Order of Execution:
        1. Query adapters strictly <= timestamp
        2. Aggregate multi-phase context
        3. Evaluate factory severity and overall risk
        4. Diagnose root causes with evidence attribution
        5. Interpret spatial flow propagation and vehicle impact
        6. Prescribe prioritized operational recommendations
        7. Assemble audit trail and return FactoryDecision contract
        """
        t = float(timestamp)

        # Overrides if provided
        p4 = phase4_adapter or self.phase4
        p5 = phase5_adapter or self.phase5
        p6 = phase6_adapter or self.phase6

        aggregator = FactoryEvidenceAggregator(
            phase4_adapter=p4,
            phase5_adapter=p5,
            phase6_adapter=p6,
        )

        # 1. Multi-Phase Evidence Aggregation
        context: FactorySnapshotContext = aggregator.aggregate_context(
            as_of_timestamp=t,
            telemetry_snapshots=telemetry_snapshots,
        )

        # 2. Factory Severity & Risk Assessment
        status, overall_risk, confidence = self.severity_engine.evaluate_severity(context)

        # 3. Root-Cause Diagnosis
        root_causes: List[RootCauseHypothesis] = self.root_cause_engine.diagnose(context)

        # Determine Primary Issue summary
        primary_issue: Optional[str] = None
        if root_causes:
            primary_issue = root_causes[0].description
        elif status != "NOMINAL":
            primary_issue = f"Factory operating with elevated risk ({status}) across active stations."

        # 4. Impact Analysis (Stations, Buffers, Vehicles)
        impact: ImpactSummary = self.impact_analyzer.analyze_impact(context)

        # 5. Operational Action Prescriptions
        recommendations: List[RecommendedActionItem] = self.recommendation_engine.generate_recommendations(
            context=context,
            root_causes=root_causes,
            impact=impact,
            factory_status=status,
        )

        # 6. Audit Trail Logging
        audit_rec = self.audit_logger.build_audit_record(
            timestamp=t,
            context=context,
            factory_status=status,
            overall_risk=overall_risk,
            root_causes=root_causes,
            recommended_actions=recommendations,
        )

        # 7. Assemble Final Contract
        return FactoryDecision(
            timestamp=t,
            factory_status=status,
            overall_risk=overall_risk,
            primary_issue=primary_issue,
            affected_stations=impact.affected_stations,
            affected_vehicles=impact.affected_vehicles,
            root_causes=root_causes,
            impact=impact,
            recommended_actions=recommendations,
            confidence=confidence,
            evidence=context.evidence_items,
            audit_trail=audit_rec,
        )
