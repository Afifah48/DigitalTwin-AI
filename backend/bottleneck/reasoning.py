from typing import List, Dict, Any, Optional
from ..models.enums import StationId
from .models import StationBottleneckRisk, BottleneckClass, BottleneckEvidence


class IndustrialReasoningEngine:
    """
    Synthesizes multi-criteria evidence, reason codes, temporal persistence, spatial propagation,
    dominance margins, and constraint migration into clear, deterministic, human-interpretable
    industrial diagnostic narratives.
    """

    STATION_NAMES = {
        StationId.S1: "S1 (Framing)",
        StationId.S2: "S2 (Paint)",
        StationId.S3: "S3 (Chassis Marriage)",
        StationId.S4: "S4 (Powertrain)",
        StationId.S5: "S5 (Interior & Wiring)",
        StationId.S6: "S6 (Final Inspection)",
    }

    def generate_station_summary(self, risk: StationBottleneckRisk) -> str:
        """Generates a concise diagnostic statement for an individual station."""
        st_name = self.STATION_NAMES.get(risk.station_id, risk.station_id.value)
        if risk.prediction == BottleneckClass.NOMINAL:
            return f"{st_name} is operating nominally within balanced takt parameters."

        reasons = []
        for ev in risk.evidence[:3]:
            if ev.signal == "cycle_time_deviation":
                reasons.append(f"cycle time deviation (+{ev.value*100:.1f}%)")
            elif ev.signal == "queue_length":
                reasons.append(f"accumulated queue ({int(ev.value)} vehicles)")
            elif ev.signal == "buffer_occupancy":
                reasons.append(f"buffer occupancy ({int(ev.value)}/5)")
            elif ev.signal == "arrival_departure_imbalance":
                reasons.append(f"flow imbalance (+{ev.value:.1f} veh/min)")
            elif ev.signal == "machine_state":
                reasons.append("machine status constraint")
            elif ev.signal == "anomaly_detection":
                reasons.append(f"Phase 4 anomaly detection (score={ev.value:.2f})")

        reasons_str = ", ".join(reasons) if reasons else "elevated operational pressure"

        ttb_str = ""
        if risk.time_to_bottleneck_seconds is not None:
            if risk.time_to_bottleneck_seconds == 0.0:
                ttb_str = " Constraint is actively limiting production."
            else:
                ttb_str = f" Estimated time to bottleneck onset: {risk.time_to_bottleneck_seconds:.0f}s ({risk.time_to_bottleneck_seconds/60:.1f} min)."

        prop_desc = ""
        if risk.affected_stations:
            affected_names = [self.STATION_NAMES.get(s, s.value) for s in risk.affected_stations]
            prop_desc = f" Constraint threatens propagation to {', '.join(affected_names)}."

        return (
            f"{st_name} is assessed at {risk.prediction.value} (Risk: {risk.risk_score:.2f}, Confidence: {risk.confidence:.2f}) "
            f"driven by {reasons_str}.{ttb_str}{prop_desc}"
        )

    def generate_factory_summary(
        self,
        primary_risk: Optional[StationBottleneckRisk],
        all_risks: List[StationBottleneckRisk],
        dominance: float = 0.0,
        constraint_migration: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generates the comprehensive factory-wide diagnostic summary."""
        if primary_risk is None or primary_risk.prediction == BottleneckClass.NOMINAL:
            return "Factory operation is nominal across all 6 stations with balanced takt flow and minimal queue accumulation."

        st_name = self.STATION_NAMES.get(primary_risk.station_id, primary_risk.station_id.value)

        # Primary drivers
        reasons = []
        for ev in primary_risk.evidence[:3]:
            if ev.signal == "cycle_time_deviation":
                reasons.append(f"cycle time is degrading (+{ev.value*100:.1f}%)")
            elif ev.signal == "queue_length":
                reasons.append(f"queue pressure is increasing ({int(ev.value)} vehicles)")
            elif ev.signal == "buffer_occupancy":
                reasons.append(f"buffer occupancy is elevated ({int(ev.value)}/5)")
            elif ev.signal == "arrival_departure_imbalance":
                reasons.append(f"inflow exceeds departure by {ev.value:.1f} veh/min")
            elif ev.signal == "machine_state":
                reasons.append("machine is experiencing unscheduled downtime")
            elif ev.signal == "anomaly_detection":
                reasons.append("sensor anomaly is persistent")

        reasons_str = ", ".join(reasons) if reasons else "operational metrics are degrading"

        # Propagation narrative
        prop_parts = []
        if primary_risk.upstream_blocking_risk > 0.35:
            prop_parts.append("upstream blocking risk")
        if primary_risk.downstream_starvation_risk > 0.35:
            prop_parts.append("downstream starvation risk")
        prop_str = f" resulting in {' and '.join(prop_parts)}" if prop_parts else ""

        # Persistence qualifier
        if primary_risk.persistence_score > 0.70:
            persist_str = "deterioration is persistent over the observation window"
        elif primary_risk.persistence_score > 0.35:
            persist_str = "deterioration is developing"
        else:
            persist_str = "early-stage anomaly under tracking"

        # Time-to-bottleneck narrative
        ttb_text = ""
        if primary_risk.time_to_bottleneck_seconds is not None:
            if primary_risk.time_to_bottleneck_seconds == 0.0:
                ttb_text = " Constraint is currently active."
            else:
                ttb_text = f" Estimated time to bottleneck onset: {primary_risk.time_to_bottleneck_seconds:.0f}s ({primary_risk.time_to_bottleneck_seconds/60:.1f} min)."

        # Dominance narrative
        dom_text = ""
        if dominance > 0.20:
            dom_text = f" {st_name} strongly dominates factory constraint (dominance margin: {dominance:.2f})."
        elif len([r for r in all_risks if r.risk_score >= 0.35]) > 1:
            dom_text = " Multi-station coupled congestion observed across adjacent stages."

        # Migration narrative
        migration_text = ""
        if constraint_migration and constraint_migration.get("migrated", False):
            prev = constraint_migration.get("previous_station")
            curr = constraint_migration.get("current_station")
            migration_text = f" Dynamic constraint migration detected: primary bottleneck shifted from {prev} to {curr}."

        return (
            f"{st_name} is assessed as the primary production bottleneck (Risk: {primary_risk.risk_score:.2f}) because {reasons_str}, "
            f"the {persist_str},{prop_str}.{ttb_text}{dom_text}{migration_text} "
            f"System confidence is {primary_risk.confidence:.2f}."
        )

