"""
Root Cause Reasoning Engine for Factory Operational Intelligence.

Analyzes multi-phase evidence to generate structured, explainable root-cause
hypotheses with confidence levels and factual evidence attribution.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.app.decision.aggregation import FactorySnapshotContext, StationOperationalContext
from backend.app.decision.schemas import DecisionEvidenceItem, RootCauseHypothesis


class FactoryRootCauseEngine:
    """
    Infers physical and operational root causes using deterministic pattern matching.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        rc_cfg = cfg.get("root_cause_thresholds", {})
        self.vib_thresh = float(rc_cfg.get("vibration_anomaly_threshold", 0.25))
        self.temp_thresh = float(rc_cfg.get("temperature_anomaly_threshold", 75.0))
        self.curr_var_thresh = float(rc_cfg.get("current_variance_threshold", 0.20))
        self.ct_delta_thresh = float(rc_cfg.get("cycle_time_delta_threshold", 10.0))
        self.buf_sat_thresh = float(rc_cfg.get("buffer_saturation_threshold", 8.5))
        self.buf_starve_thresh = float(rc_cfg.get("buffer_starvation_threshold", 1.0))

    def diagnose(
        self,
        context: FactorySnapshotContext,
    ) -> List[RootCauseHypothesis]:
        """
        Evaluates the factory context and returns ranked root-cause hypotheses.
        """
        hypotheses: List[RootCauseHypothesis] = []

        # 1. Evaluate Station-level Physical Issues
        for st_id, st_ctx in context.stations.items():
            # Pattern 1: Progressive Mechanical / Bearing Degradation
            if (st_ctx.vibration >= self.vib_thresh and st_ctx.current_variance >= self.curr_var_thresh) or (st_ctx.cycle_time_delta >= self.ct_delta_thresh and st_ctx.is_anomalous):
                ev = [
                    DecisionEvidenceItem(
                        signal="Vibration Amplitude",
                        value=st_ctx.vibration,
                        source="Telemetry",
                        direction="ELEVATED",
                        strength=min(1.0, st_ctx.vibration / 0.50),
                        station_id=st_id,
                    ),
                    DecisionEvidenceItem(
                        signal="Motor Current Variance",
                        value=st_ctx.current_variance,
                        source="Telemetry",
                        direction="ELEVATED",
                        strength=min(1.0, st_ctx.current_variance / 0.50),
                        station_id=st_id,
                    ),
                    DecisionEvidenceItem(
                        signal="Cycle Time Deviation",
                        value=st_ctx.cycle_time_delta,
                        source="Telemetry",
                        direction="DEGRADED",
                        strength=min(1.0, st_ctx.cycle_time_delta / 20.0),
                        station_id=st_id,
                    ),
                ]
                conf = min(0.95, 0.50 + 0.25 * (1 if st_ctx.is_anomalous else 0) + 0.20 * (1 if st_ctx.is_bottleneck else 0))
                hypotheses.append(
                    RootCauseHypothesis(
                        hypothesis_id=f"RC_MECH_{st_id}",
                        category="MECHANICAL_DEGRADATION",
                        station_id=st_id,
                        description=f"Station {st_id} is exhibiting progressive mechanical bearing/spindle degradation, driving elevated vibration, current variance, and cycle-time expansion.",
                        confidence=conf,
                        supporting_evidence=ev,
                    )
                )

            # Pattern 2: Sudden Tool Breakdown / Jam
            elif st_ctx.machine_state in ("DOWN", "FAULT", "ERROR") or (st_ctx.motor_current >= 15.0 and st_ctx.is_anomalous):
                ev = [
                    DecisionEvidenceItem(
                        signal="Machine State",
                        value=st_ctx.machine_state,
                        source="Telemetry",
                        direction="DEGRADED",
                        strength=1.0,
                        station_id=st_id,
                    ),
                    DecisionEvidenceItem(
                        signal="Motor Current Surge",
                        value=st_ctx.motor_current,
                        source="Telemetry",
                        direction="ELEVATED",
                        strength=min(1.0, st_ctx.motor_current / 20.0),
                        station_id=st_id,
                    ),
                ]
                hypotheses.append(
                    RootCauseHypothesis(
                        hypothesis_id=f"RC_BREAKDOWN_{st_id}",
                        category="SUDDEN_TOOL_BREAKDOWN",
                        station_id=st_id,
                        description=f"Station {st_id} has experienced a sudden tool breakage or mechanical jam, triggering emergency shutdown and line interruption.",
                        confidence=0.98,
                        supporting_evidence=ev,
                    )
                )

            # Pattern 3: Welding / Fixture Alignment Jitter
            elif st_ctx.vibration >= 0.15 and "weld" in st_id.lower() or (st_id == "S5" and st_ctx.is_anomalous):
                ev = [
                    DecisionEvidenceItem(
                        signal="Weld Station Vibration",
                        value=st_ctx.vibration,
                        source="Telemetry",
                        direction="ELEVATED",
                        strength=0.75,
                        station_id=st_id,
                    )
                ]
                hypotheses.append(
                    RootCauseHypothesis(
                        hypothesis_id=f"RC_WELD_{st_id}",
                        category="WELDING_ALIGNMENT_JITTER",
                        station_id=st_id,
                        description=f"Station {st_id} is experiencing fixture play or weld tip vibration jitter, increasing clearance gap defect risk.",
                        confidence=0.82,
                        supporting_evidence=ev,
                    )
                )

        # 2. Evaluate Line Flow & Buffer Dynamics
        for st_id, st_ctx in context.stations.items():
            if st_ctx.upstream_blocking_risk >= 0.60 or st_ctx.buffer_occupancy >= self.buf_sat_thresh:
                ev = [
                    DecisionEvidenceItem(
                        signal="Buffer Saturation",
                        value=st_ctx.buffer_occupancy,
                        source="Phase 5 Bottleneck",
                        direction="SATURATED",
                        strength=min(1.0, st_ctx.buffer_occupancy / 10.0),
                        station_id=st_id,
                    )
                ]
                hypotheses.append(
                    RootCauseHypothesis(
                        hypothesis_id=f"RC_BLOCK_{st_id}",
                        category="UPSTREAM_FLOW_BLOCKING",
                        station_id=st_id,
                        description=f"Buffer near Station {st_id} is saturating due to downstream processing constraint, threatening upstream station blockage.",
                        confidence=0.88,
                        supporting_evidence=ev,
                    )
                )

        # 3. Evaluate Vehicle Quality Consequences
        high_v = context.high_risk_vehicles
        if high_v:
            ev = [
                DecisionEvidenceItem(
                    signal=f"Affected High-Risk Vehicles ({len(high_v)})",
                    value=len(high_v),
                    source="Phase 6 Quality",
                    direction="ELEVATED",
                    strength=min(1.0, len(high_v) / 4.0),
                    station_id=context.primary_bottleneck_station,
                )
            ]
            hypotheses.append(
                RootCauseHypothesis(
                    hypothesis_id="RC_QUALITY_PROPAGATION",
                    category="VEHICLE_QUALITY_EXPOSURE",
                    station_id=context.primary_bottleneck_station,
                    description=f"{len(high_v)} vehicles processed during the abnormal station conditions exhibit high defect probability and require containment.",
                    confidence=0.92,
                    supporting_evidence=ev,
                )
            )

        # Sort hypotheses by confidence descending
        return sorted(hypotheses, key=lambda h: h.confidence, reverse=True)
