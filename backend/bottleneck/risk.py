import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from .models import AnomalyPrediction, BottleneckEvidence, BottleneckClass, ReasonCode
from ..models.enums import StationId, MachineState


class BottleneckRiskEngine:
    """
    Deterministic Multi-Criteria Bottleneck Risk Scoring Engine.
    Combines cycle-time pressure, queue buildup, buffer occupancy, flow imbalance,
    machine status, and Phase 4 anomaly detection evidence into an interpretable score.
    All six component scores are computed before any branching to prevent UnboundLocalError.
    """

    def __init__(
        self,
        weight_cycle: float = 0.30,
        weight_queue: float = 0.25,
        weight_buffer: float = 0.15,
        weight_flow: float = 0.10,
        weight_state: float = 0.10,
        weight_anomaly: float = 0.10,
    ):
        self.w_cycle = weight_cycle
        self.w_queue = weight_queue
        self.w_buffer = weight_buffer
        self.w_flow = weight_flow
        self.w_state = weight_state
        self.w_anomaly = weight_anomaly

    def compute_time_to_bottleneck(
        self,
        telemetry: Dict[str, Any],
        risk_score: float,
        m_state: str,
        q_len: int,
        q_growth: float,
        buf_occ: int,
        buf_cap: int,
        imbalance: float,
        ct_dev: float,
        ct_trend: float,
    ) -> Optional[float]:
        """
        Calculates estimated time in seconds until the station becomes a hard bottleneck constraint.
        Uses first-principles physical arrival/departure flows, queue growth rates, and buffer capacity.
        Strictly causal and free of future-data leakage.
        """
        # If machine is currently down or station is already under active critical bottleneck
        if m_state in ("DOWN", "MAINTENANCE", "MICRO_STOP") or risk_score >= 0.70 or q_len >= 4 or buf_occ >= 5:
            return 0.0

        if risk_score < 0.22 and q_growth <= 0 and imbalance <= 0 and ct_trend <= 0:
            return None  # Nominal operation; no imminent bottleneck

        ttb_estimates: List[float] = []

        # 1. Queue capacity saturation time: time until queue reaches critical threshold (4 vehicles)
        if q_growth > 0.05 and q_len < 4:
            # q_growth is delta vehicles per snapshot interval (30s)
            remaining_q = 4.0 - float(q_len)
            time_q_seconds = (remaining_q / q_growth) * 30.0
            if 0.0 <= time_q_seconds <= 1800.0:
                ttb_estimates.append(time_q_seconds)

        # 2. Buffer capacity saturation time: time until buffer reaches capacity (5 vehicles)
        if imbalance > 0.10 and buf_occ < buf_cap:
            # imbalance in veh/min -> veh/sec = imbalance / 60.0
            remaining_buf = float(buf_cap - buf_occ)
            time_buf_seconds = remaining_buf / (imbalance / 60.0)
            if 0.0 <= time_buf_seconds <= 1800.0:
                ttb_estimates.append(time_buf_seconds)

        # 3. Cycle time degradation horizon: time until cycle time deviation crosses +25%
        if ct_trend > 0.1 and ct_dev < 0.25:
            remaining_dev = 0.25 - ct_dev
            time_ct_seconds = (remaining_dev / ct_trend) * 30.0
            if 0.0 <= time_ct_seconds <= 1800.0:
                ttb_estimates.append(time_ct_seconds)

        if not ttb_estimates:
            if risk_score >= 0.35:
                # Elevated risk without explicit linear growth gradient: conservative estimate inversely scaled by risk
                scaled_ttb = max(30.0, (1.0 - risk_score) * 600.0)
                return round(scaled_ttb, 1)
            return None

        # Return the earliest physical bottleneck projection
        return round(float(np.clip(min(ttb_estimates), 0.0, 1800.0)), 1)

    def extract_reason_codes(
        self,
        telemetry: Dict[str, Any],
        anomaly: Optional[AnomalyPrediction],
        risk_score: float,
        evidence_list: List[BottleneckEvidence],
    ) -> List[str]:
        """Extracts structured categorical reason codes from telemetry and evidence."""
        codes: List[str] = []
        m_state = telemetry.get("machine_state", "IDLE")
        if isinstance(m_state, MachineState):
            m_state = m_state.value

        if m_state in ("DOWN", "MAINTENANCE", "MICRO_STOP"):
            codes.append(ReasonCode.MACHINE_DOWNTIME.value)
        elif m_state == "BLOCKED":
            codes.append(ReasonCode.UPSTREAM_BLOCKING.value)
        elif m_state == "STARVED":
            codes.append(ReasonCode.DOWNSTREAM_STARVATION.value)

        ct_dev = float(telemetry.get("cycle_time_deviation", 0.0))
        if ct_dev > 0.04:
            codes.append(ReasonCode.CYCLE_TIME_DEGRADATION.value)

        q_len = int(telemetry.get("queue_length", 0))
        q_growth = float(telemetry.get("queue_growth_rate", 0.0))
        if q_len >= 2 or q_growth > 0.2:
            codes.append(ReasonCode.QUEUE_ACCUMULATION.value)

        buf_occ = int(telemetry.get("buffer_occupancy", 0))
        buf_press = float(telemetry.get("buffer_pressure", 0.0))
        if buf_occ >= 3 or buf_press >= 0.60:
            codes.append(ReasonCode.BUFFER_SATURATION.value)

        imbalance = float(telemetry.get("arrival_departure_imbalance", 0.0))
        if imbalance > 0.3:
            codes.append(ReasonCode.FLOW_IMBALANCE.value)

        if anomaly is not None and (anomaly.detected or anomaly.anomaly_score > 0.4):
            codes.append(ReasonCode.PHASE4_ANOMALY.value)

        return list(dict.fromkeys(codes))

    def compute_station_risk(
        self,
        telemetry: Dict[str, Any],
        anomaly: Optional[AnomalyPrediction] = None,
    ) -> Tuple[float, float, List[BottleneckEvidence], Dict[str, float]]:
        """
        Computes station bottleneck risk score, confidence, attributed evidence, and raw component scores.
        All six components are computed fully before any decision branching.
        Returns:
            (risk_score, confidence, evidence_list, components_dict)
        """
        evidence_list: List[BottleneckEvidence] = []
        components: Dict[str, float] = {}

        # ──────────────────────────────────────────────────────────────────────
        # 1. Cycle-Time Pressure
        # ──────────────────────────────────────────────────────────────────────
        ct = float(telemetry.get("cycle_time", 54.0))
        base_ct = float(telemetry.get("baseline_cycle_time", 54.0))
        ct_dev = float(telemetry.get("cycle_time_deviation", (ct - base_ct) / max(1.0, base_ct)))
        ct_trend = float(telemetry.get("cycle_time_trend", 0.0))

        dev_score = float(np.clip(ct_dev / 0.35, 0.0, 1.0)) if ct_dev > 0 else 0.0
        trend_score = float(np.clip(ct_trend / 5.0, 0.0, 1.0)) if ct_trend > 0 else 0.0
        s_cycle = float(np.clip(0.75 * dev_score + 0.25 * trend_score, 0.0, 1.0))
        components["cycle_time_pressure"] = round(s_cycle, 4)

        if ct_dev > 0.04:
            evidence_list.append(
                BottleneckEvidence(
                    signal="cycle_time_deviation",
                    value=round(ct_dev, 3),
                    normalized_strength=round(dev_score, 3),
                    direction="increasing" if ct_trend >= 0 else "elevated",
                    source="TELEMETRY",
                )
            )

        # ──────────────────────────────────────────────────────────────────────
        # 2. Queue Pressure
        # ──────────────────────────────────────────────────────────────────────
        q_len = int(telemetry.get("queue_length", 0))
        q_growth = float(telemetry.get("queue_growth_rate", 0.0))

        q_ratio = float(np.clip(q_len / 4.0, 0.0, 1.0))
        q_growth_score = float(np.clip(q_growth / 1.5, 0.0, 1.0)) if q_growth > 0 else 0.0
        s_queue = float(np.clip(0.60 * q_ratio + 0.40 * q_growth_score, 0.0, 1.0))
        components["queue_pressure"] = round(s_queue, 4)

        if q_len >= 2 or q_growth > 0.2:
            evidence_list.append(
                BottleneckEvidence(
                    signal="queue_length",
                    value=float(q_len),
                    normalized_strength=round(s_queue, 3),
                    direction="increasing" if q_growth > 0 else "elevated",
                    source="QUEUE",
                )
            )

        # ──────────────────────────────────────────────────────────────────────
        # 3. Buffer Pressure
        # ──────────────────────────────────────────────────────────────────────
        buf_occ = int(telemetry.get("buffer_occupancy", 0))
        buf_cap = max(1, int(telemetry.get("buffer_capacity", 5)))
        buf_press = float(telemetry.get("buffer_pressure", buf_occ / buf_cap))
        s_buffer = float(np.clip(buf_press / 0.80, 0.0, 1.0))
        components["buffer_pressure"] = round(s_buffer, 4)

        if buf_occ >= 3:
            evidence_list.append(
                BottleneckEvidence(
                    signal="buffer_occupancy",
                    value=float(buf_occ),
                    normalized_strength=round(s_buffer, 3),
                    direction="increasing" if buf_occ >= 4 else "elevated",
                    source="BUFFER",
                )
            )

        # ──────────────────────────────────────────────────────────────────────
        # 4. Flow Imbalance
        # ──────────────────────────────────────────────────────────────────────
        arr_rate = float(telemetry.get("arrival_rate", 0.0))
        dep_rate = float(telemetry.get("departure_rate", 0.0))
        imbalance = float(telemetry.get("arrival_departure_imbalance", arr_rate - dep_rate))

        s_flow = float(np.clip(imbalance / 1.5, 0.0, 1.0)) if imbalance > 0 else 0.0
        components["flow_imbalance"] = round(s_flow, 4)

        if imbalance > 0.3:
            evidence_list.append(
                BottleneckEvidence(
                    signal="arrival_departure_imbalance",
                    value=round(imbalance, 2),
                    normalized_strength=round(s_flow, 3),
                    direction="increasing",
                    source="FLOW",
                )
            )

        # ──────────────────────────────────────────────────────────────────────
        # 5. Phase 4 Anomaly Evidence (computed BEFORE machine-state branching)
        # ──────────────────────────────────────────────────────────────────────
        s_anomaly = 0.0
        if anomaly is not None:
            # Tolerates null anomaly_probability without error
            if anomaly.anomaly_probability is not None:
                s_anomaly = float(np.clip(anomaly.anomaly_probability, 0.0, 1.0))
            else:
                s_anomaly = float(np.clip(anomaly.anomaly_score, 0.0, 1.0))

            if anomaly.detected or s_anomaly > 0.4:
                evidence_list.append(
                    BottleneckEvidence(
                        signal="anomaly_detection",
                        value=round(s_anomaly, 3),
                        normalized_strength=round(s_anomaly, 3),
                        direction="elevated" if s_anomaly < 0.7 else "critical",
                        source="ANOMALY",
                    )
                )
                for top_sig in anomaly.top_signals:
                    evidence_list.append(
                        BottleneckEvidence(
                            signal=f"top_anomaly_signal_{top_sig}",
                            value=1.0,
                            normalized_strength=0.5,
                            direction="elevated",
                            source="ANOMALY",
                        )
                    )
        components["anomaly_score"] = round(s_anomaly, 4)

        # ──────────────────────────────────────────────────────────────────────
        # 6. Machine State — evaluated last; DOWN overrides full score
        # ──────────────────────────────────────────────────────────────────────
        m_state = telemetry.get("machine_state", MachineState.IDLE.value)
        if isinstance(m_state, MachineState):
            m_state = m_state.value

        if m_state in ("DOWN", "MAINTENANCE", "MICRO_STOP"):
            s_state = 1.0
            evidence_list.append(
                BottleneckEvidence(
                    signal="machine_state",
                    value=1.0,
                    normalized_strength=1.0,
                    direction="critical",
                    source="STATE",
                )
            )
            components["machine_state_score"] = round(s_state, 4)

            # Machine stoppage is a direct flow constraint — dominate the risk score immediately
            # without waiting for queue buildup. Anomaly evidence can further boost (up to 0.85).
            risk_score = float(np.clip(0.65 + 0.20 * s_anomaly, 0.0, 1.0))
            confidence = float(np.clip(
                0.95 - (0.35 if telemetry.get("sensor_missing_flag", False) else 0.0),
                0.10, 1.0,
            ))
            return round(risk_score, 4), round(confidence, 4), evidence_list, components

        elif m_state == "BLOCKED":
            # Blocked is an upstream propagation symptom — moderate direct bottleneck indicator
            s_state = 0.50
        elif m_state == "STARVED":
            # Starved means downstream is short of input — low direct bottleneck score
            s_state = 0.10
        elif m_state == "RUNNING" and s_cycle > 0.5:
            # Running but under high cycle pressure — active constraint
            s_state = 0.70
        else:
            s_state = 0.0
        components["machine_state_score"] = round(s_state, 4)

        # ──────────────────────────────────────────────────────────────────────
        # 7. Weighted Multi-Criteria Combination
        # ──────────────────────────────────────────────────────────────────────
        raw_risk = (
            self.w_cycle * s_cycle
            + self.w_queue * s_queue
            + self.w_buffer * s_buffer
            + self.w_flow * s_flow
            + self.w_state * s_state
            + self.w_anomaly * s_anomaly
        )

        # Co-activation coupling: cycle pressure + queue pressure jointly exceed sum of parts
        if s_cycle > 0.4 and s_queue > 0.4:
            coupling_boost = 0.20 * min(s_cycle, s_queue)
            raw_risk = min(1.0, raw_risk + coupling_boost)

        risk_score = float(np.clip(raw_risk, 0.0, 1.0))

        # ──────────────────────────────────────────────────────────────────────
        # 8. Telemetry Confidence
        # ──────────────────────────────────────────────────────────────────────
        base_confidence = 0.95
        if telemetry.get("sensor_missing_flag", False):
            base_confidence -= 0.35

        inst_level = telemetry.get("instrumentation_level", "HIGH")
        if inst_level == "LOW":
            base_confidence -= 0.20
        elif inst_level == "MEDIUM":
            base_confidence -= 0.08

        # Slight penalty when Phase 4 omits calibrated probability
        if anomaly is not None and anomaly.anomaly_probability is None and anomaly.detected:
            base_confidence -= 0.05

        confidence = float(np.clip(base_confidence, 0.10, 1.0))

        return round(risk_score, 4), round(confidence, 4), evidence_list, components


