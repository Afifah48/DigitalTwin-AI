from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd


from ..models.enums import StationId, BufferId, MachineState
from .models import (
    AnomalyPrediction,
    StationBottleneckRisk,
    FactoryBottleneckAnalysis,
    BottleneckClass,
    PropagationDirection,
)
from .risk import BottleneckRiskEngine
from .persistence import TemporalPersistenceTracker
from .propagation import SpatialPropagationAnalyzer
from .reasoning import IndustrialReasoningEngine
from .ranking import StationRanker


class Phase4AnomalyProvider(ABC):
    """
    Abstract Service Interface for Phase 4 Anomaly Detection.
    Allows Phase 5 to consume anomaly signals without depending on Isolation Forest or LSTM internals.
    """

    @abstractmethod
    def get_anomaly_prediction(
        self,
        station_id: StationId,
        timestamp: float,
        telemetry: Dict[str, Any],
    ) -> Optional[AnomalyPrediction]:
        pass


class Phase4ServiceAdapter(Phase4AnomalyProvider):
    """
    Adapter between the Phase 4 AnomalyService and the Phase 5 bottleneck pipeline.

    Phase 5 consumes only the stable AnomalyPrediction contract and does not
    access Isolation Forest, LSTM, scaler, threshold, or other Phase 4 internals.
    """

    def __init__(self, phase4_service):
        self.phase4_service = phase4_service

    def get_anomaly_prediction(
        self,
        station_id: StationId,
        timestamp: float,
        telemetry: Dict[str, Any],
    ) -> Optional[AnomalyPrediction]:

        prediction = self.phase4_service.predict_station(
            station_id=station_id.value,
            timestamp=timestamp,
            station_telemetry=telemetry,
        )

        if prediction is None:
            return None

        return AnomalyPrediction(
            station_id=station_id,
            timestamp=float(prediction.timestamp),
            anomaly_score=float(prediction.anomaly_score),
            anomaly_probability=(
                float(prediction.anomaly_probability)
                if prediction.anomaly_probability is not None
                else None
            ),
            severity=(
                prediction.severity.value
                if hasattr(prediction.severity, "value")
                else str(prediction.severity)
            ),
            detected=bool(prediction.detected),
            lead_time_if_known=prediction.lead_time_if_known,
            top_signals=list(prediction.top_signals or []),
        )


class BottleneckPipeline:
    """
    End-to-End Bottleneck Prediction, Temporal Persistence & Spatial Propagation Pipeline.
    """

    ALL_STATIONS = [
        StationId.S1,
        StationId.S2,
        StationId.S3,
        StationId.S4,
        StationId.S5,
        StationId.S6,
    ]

    def __init__(
        self,
        anomaly_provider: Optional[Phase4AnomalyProvider] = None,
        risk_engine: Optional[BottleneckRiskEngine] = None,
        persistence_tracker: Optional[TemporalPersistenceTracker] = None,
        propagation_analyzer: Optional[SpatialPropagationAnalyzer] = None,
        reasoning_engine: Optional[IndustrialReasoningEngine] = None,
    ):
        self.anomaly_provider = anomaly_provider 
        self.risk_engine = risk_engine or BottleneckRiskEngine()
        self.persistence = persistence_tracker or TemporalPersistenceTracker()
        self.propagation = propagation_analyzer or SpatialPropagationAnalyzer()
        self.reasoning = reasoning_engine or IndustrialReasoningEngine()
        self._prev_bottleneck_station: Optional[StationId] = None
        self._prev_bottleneck_time: Optional[float] = None

    def reset(self):
        """Resets pipeline temporal trackers for a clean episode run."""
        self.persistence.reset()
        self._prev_bottleneck_station = None
        self._prev_bottleneck_time = None

    def analyze_snapshot(
        self,
        timestamp: float,
        station_telemetries: Dict[StationId, Dict[str, Any]],
        buffer_occupancies: Optional[Dict[BufferId, int]] = None,
        anomaly_predictions: Optional[Dict[StationId, AnomalyPrediction]] = None,
    ) -> FactoryBottleneckAnalysis:
        """
        Analyzes factory state at snapshot timestamp t (using only data <= t).
        """
        buf_occs = buffer_occupancies or {}
        if not buf_occs:
            # Extract buffer occupancies from station telemetries if present
            for st_id, tel in station_telemetries.items():
                b_occ = tel.get("buffer_occupancy", 0)
                if st_id == StationId.S1:
                    buf_occs[BufferId.B12] = b_occ
                elif st_id == StationId.S2:
                    buf_occs[BufferId.B23] = b_occ
                elif st_id == StationId.S3:
                    buf_occs[BufferId.B34] = b_occ
                elif st_id == StationId.S4:
                    buf_occs[BufferId.B45] = b_occ
                elif st_id == StationId.S5:
                    buf_occs[BufferId.B56] = b_occ

        station_risks: List[StationBottleneckRisk] = []

        for st_id in self.ALL_STATIONS:
            tel = station_telemetries.get(st_id, {})
            # Query anomaly prediction from provider or passed dictionary
            anomaly = None
            if anomaly_predictions and st_id in anomaly_predictions:
                anomaly = anomaly_predictions[st_id]
            elif self.anomaly_provider:
                anomaly = self.anomaly_provider.get_anomaly_prediction(st_id, timestamp, tel)

            # 1. Compute multi-criteria instantaneous risk score, reason codes, and time-to-bottleneck
            inst_risk, conf, evidence, comp = self.risk_engine.compute_station_risk(tel, anomaly)
            st_reason_codes = self.risk_engine.extract_reason_codes(tel, anomaly, inst_risk, evidence)

            m_state = tel.get("machine_state", "IDLE")
            if isinstance(m_state, MachineState):
                m_state = m_state.value

            time_to_bottleneck = self.risk_engine.compute_time_to_bottleneck(
                telemetry=tel,
                risk_score=inst_risk,
                m_state=m_state,
                q_len=int(tel.get("queue_length", 0)),
                q_growth=float(tel.get("queue_growth_rate", 0.0)),
                buf_occ=int(tel.get("buffer_occupancy", 0)),
                buf_cap=max(1, int(tel.get("buffer_capacity", 5))),
                imbalance=float(tel.get("arrival_departure_imbalance", 0.0)),
                ct_dev=float(tel.get("cycle_time_deviation", 0.0)),
                ct_trend=float(tel.get("cycle_time_trend", 0.0)),
            )

            # 2. Update and evaluate temporal persistence
            persist_score = self.persistence.update_and_evaluate(st_id, timestamp, inst_risk)
            eff_risk = self.persistence.get_smoothed_risk(st_id, inst_risk, persist_score)

            # 3. Analyze spatial constraint propagation
            up_risk, down_risk, prop_score, affected_sts, _ = self.propagation.analyze_station_propagation(
                station_id=st_id,
                station_risk=eff_risk,
                buffer_occupancies=buf_occs,
            )

            # Build station bottleneck risk assessment
            st_risk_record = StationBottleneckRisk(
                station_id=st_id,
                timestamp=timestamp,
                risk_score=eff_risk,
                prediction=StationRanker.classify_risk(eff_risk),
                confidence=conf,
                persistence_score=persist_score,
                anomaly_score=anomaly.anomaly_score if anomaly else 0.0,
                anomaly_probability=anomaly.anomaly_probability if anomaly else None,
                anomaly_detected=anomaly.detected if anomaly else False,
                reason_codes=st_reason_codes,
                time_to_bottleneck_seconds=time_to_bottleneck,
                evidence=evidence,
                upstream_blocking_risk=up_risk,
                downstream_starvation_risk=down_risk,
                propagation_score=prop_score,
                affected_stations=affected_sts,
            )
            station_risks.append(st_risk_record)

        # 4. Rank stations from highest to lowest risk
        ranked_risks = StationRanker.rank_stations(station_risks)
        primary_bottleneck = StationRanker.get_primary_bottleneck(ranked_risks)
        dominance = StationRanker.compute_bottleneck_dominance(ranked_risks)
        active_bottlenecks = StationRanker.identify_active_bottlenecks(ranked_risks)

        # 5. Detect and track dynamic constraint migration
        migration_info = None
        current_primary_id = primary_bottleneck.station_id if primary_bottleneck else None

        if (
            self._prev_bottleneck_station is not None
            and current_primary_id is not None
            and self._prev_bottleneck_station != current_primary_id
        ):
            migration_info = {
                "migrated": True,
                "previous_station": self._prev_bottleneck_station.value,
                "current_station": current_primary_id.value,
                "timestamp": timestamp,
            }

        self._prev_bottleneck_station = current_primary_id
        self._prev_bottleneck_time = timestamp

        # 6. Generate industrial reasoning summary
        summary = self.reasoning.generate_factory_summary(
            primary_bottleneck,
            ranked_risks,
            dominance=dominance,
            constraint_migration=migration_info,
        )

        # Aggregate propagation mapping
        prop_summary = {}
        if primary_bottleneck and primary_bottleneck.affected_stations:
            prop_summary = {
                "source": primary_bottleneck.station_id.value,
                "upstream_blocking_risk": primary_bottleneck.upstream_blocking_risk,
                "downstream_starvation_risk": primary_bottleneck.downstream_starvation_risk,
                "affected_stations": [s.value for s in primary_bottleneck.affected_stations],
            }

        return FactoryBottleneckAnalysis(
            timestamp=timestamp,
            predicted_bottleneck_station=current_primary_id,
            predicted_bottleneck_risk=primary_bottleneck.risk_score if primary_bottleneck else 0.0,
            bottleneck_dominance=dominance,
            active_bottlenecks=active_bottlenecks,
            confidence=primary_bottleneck.confidence if primary_bottleneck else 1.0,
            estimated_time_to_bottleneck_seconds=primary_bottleneck.time_to_bottleneck_seconds if primary_bottleneck else None,
            station_ranking=ranked_risks,
            propagation=prop_summary,
            constraint_migration=migration_info,
            summary=summary,
        )

    def analyze_dataframe(
        self,
        telemetry_df: pd.DataFrame,
    ) -> List[FactoryBottleneckAnalysis]:
        """
        Runs batch chronological inference over an episode telemetry DataFrame.
        """
        self.reset()
        analyses = []
        timestamps = sorted(telemetry_df["timestamp"].unique())

        for t in timestamps:
            t_df = telemetry_df[telemetry_df["timestamp"] == t]
            station_tels: Dict[StationId, Dict[str, Any]] = {}
            for _, row in t_df.iterrows():
                st_id = StationId(row["station_id"]) if isinstance(row["station_id"], str) else row["station_id"]
                station_tels[st_id] = row.to_dict()

            analysis = self.analyze_snapshot(t, station_tels)
            analyses.append(analysis)

        return analyses

