from typing import List, Optional
from ..models.enums import StationId
from .models import StationBottleneckRisk, BottleneckClass


class StationRanker:
    """
    Ranks all factory stations by effective bottleneck risk, classifies risk bands,
    computes bottleneck dominance margins, and identifies active bottlenecks.
    """

    @staticmethod
    def classify_risk(risk_score: float) -> BottleneckClass:
        if risk_score >= 0.75:
            return BottleneckClass.CRITICAL
        elif risk_score >= 0.55:
            return BottleneckClass.HIGH_RISK
        elif risk_score >= 0.38:
            return BottleneckClass.MEDIUM_RISK
        elif risk_score >= 0.22:
            return BottleneckClass.LOW_RISK
        return BottleneckClass.NOMINAL

    @classmethod
    def rank_stations(
        cls,
        station_risks: List[StationBottleneckRisk],
    ) -> List[StationBottleneckRisk]:
        """Sorts stations in descending order of risk score, updating risk classes."""
        for r in station_risks:
            r.prediction = cls.classify_risk(r.risk_score)

        return sorted(station_risks, key=lambda s: s.risk_score, reverse=True)

    @classmethod
    def get_primary_bottleneck(
        cls,
        ranked_risks: List[StationBottleneckRisk],
        threshold: float = 0.35,
    ) -> Optional[StationBottleneckRisk]:
        """Returns the primary bottleneck station if top risk exceeds threshold, else None."""
        if not ranked_risks:
            return None
        top = ranked_risks[0]
        if top.risk_score >= threshold:
            return top
        return None

    @classmethod
    def compute_bottleneck_dominance(
        cls,
        ranked_risks: List[StationBottleneckRisk],
        threshold: float = 0.35,
    ) -> float:
        """
        Computes the dominance margin of the primary bottleneck over the next most constrained station.
        Returns a value in [0.0, 1.0]. A high dominance (> 0.25) indicates a single isolated bottleneck constraint.
        A low dominance (< 0.10) with elevated risks indicates distributed line congestion.
        If top station does not exceed bottleneck threshold, dominance is 0.0.
        """
        if not ranked_risks or len(ranked_risks) < 2:
            return 0.0
        top = ranked_risks[0]
        if top.risk_score < threshold:
            return 0.0
        second = ranked_risks[1]
        margin = max(0.0, top.risk_score - second.risk_score)
        return round(float(margin), 4)


    @classmethod
    def identify_active_bottlenecks(
        cls,
        ranked_risks: List[StationBottleneckRisk],
        threshold: float = 0.35,
    ) -> List[StationId]:
        """Identifies all stations currently exceeding the operational bottleneck threshold."""
        return [r.station_id for r in ranked_risks if r.risk_score >= threshold]

