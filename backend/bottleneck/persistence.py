from typing import Dict, List, Any, Optional
from collections import defaultdict
import numpy as np
from ..models.enums import StationId


class TemporalPersistenceTracker:
    """
    Tracks station-level historical evidence accumulation over rolling observation windows.
    Suppresses single-snapshot transient noise and reinforces sustained process deterioration.
    """

    def __init__(
        self,
        history_window_size: int = 15,  # 15 snapshots * 30s = 7.5 minutes
        consecutive_threshold: int = 4,  # minimum consecutive elevated snapshots for full persistence
        decay_factor: float = 0.85,
    ):
        self.window_size = history_window_size
        self.consecutive_threshold = consecutive_threshold
        self.decay_factor = decay_factor

        # Internal state per station: list of historical (timestamp, instantaneous_risk)
        self._history: Dict[StationId, List[Dict[str, float]]] = defaultdict(list)
        self._smoothed_risk: Dict[StationId, float] = defaultdict(float)

    def reset(self):
        """Clears all historical tracks for a new episode."""
        self._history.clear()
        self._smoothed_risk.clear()

    def update_and_evaluate(
        self,
        station_id: StationId,
        timestamp: float,
        instantaneous_risk: float,
    ) -> float:
        """
        Updates station temporal history with current instantaneous risk and returns persistence score [0.0, 1.0].
        Strictly consumes only observations <= timestamp.
        """
        st_history = self._history[station_id]
        st_history.append({"timestamp": timestamp, "risk": instantaneous_risk})

        # Maintain bounded window
        if len(st_history) > self.window_size:
            st_history.pop(0)

        # 1. Count consecutive snapshots above elevated risk threshold (>= 0.35)
        consecutive_count = 0
        for entry in reversed(st_history):
            if entry["risk"] >= 0.35:
                consecutive_count += 1
            else:
                break

        # 2. Ratio of elevated snapshots in recent window
        elevated_count = sum(1 for e in st_history if e["risk"] >= 0.35)
        window_elevated_ratio = elevated_count / max(1, len(st_history))

        # 3. Exponential Moving Average (EMA) smoothed risk
        prev_smoothed = self._smoothed_risk[station_id]
        if len(st_history) == 1:
            new_smoothed = instantaneous_risk
        else:
            new_smoothed = (1.0 - self.decay_factor) * instantaneous_risk + self.decay_factor * prev_smoothed
        self._smoothed_risk[station_id] = new_smoothed

        # 4. Persistence Score calculation
        consecutive_factor = min(1.0, consecutive_count / float(self.consecutive_threshold))
        persistence_score = 0.60 * consecutive_factor + 0.40 * window_elevated_ratio

        # If only 1 observation exists, damp persistence slightly
        if len(st_history) <= 2:
            persistence_score *= 0.50

        return float(np.clip(round(persistence_score, 4), 0.0, 1.0))

    def get_smoothed_risk(self, station_id: StationId, instantaneous_risk: float, persistence_score: float) -> float:
        """
        Combines instantaneous risk with temporal persistence to compute the effective smoothed risk.
        Single spikes are dampened; sustained deterioration is fully preserved.
        Critical events (risk >= 0.60) bypass dampening to ensure immediate detection.
        """
        # Critical events (machine DOWN, total buffer saturation) must not be dampened
        if instantaneous_risk >= 0.60:
            return float(np.clip(round(instantaneous_risk, 4), 0.0, 1.0))

        # If persistence is very high, trust instantaneous risk fully; if low, dampen toward smoothed
        alpha = 0.40 + 0.60 * persistence_score
        effective_risk = alpha * instantaneous_risk + (1.0 - alpha) * self._smoothed_risk[station_id]
        return float(np.clip(round(effective_risk, 4), 0.0, 1.0))
