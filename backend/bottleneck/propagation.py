from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from ..models.enums import StationId, BufferId
from .models import PropagationDirection


class SpatialPropagationAnalyzer:
    """
    Graph-based Factory Topology Analyzer for Spatial Constraint Propagation.
    Computes upstream blocking and downstream starvation propagation risks symmetrically
    for any station across the sequential manufacturing line without station-specific hardcoding.
    """

    STATION_SEQUENCE: List[StationId] = [
        StationId.S1,
        StationId.S2,
        StationId.S3,
        StationId.S4,
        StationId.S5,
        StationId.S6,
    ]

    # Map station -> (upstream_buffer, downstream_buffer)
    STATION_BUFFERS: Dict[StationId, Tuple[Optional[BufferId], Optional[BufferId]]] = {
        StationId.S1: (None, BufferId.B12),
        StationId.S2: (BufferId.B12, BufferId.B23),
        StationId.S3: (BufferId.B23, BufferId.B34),
        StationId.S4: (BufferId.B34, BufferId.B45),
        StationId.S5: (BufferId.B45, BufferId.B56),
        StationId.S6: (BufferId.B56, None),
    }

    def analyze_station_propagation(
        self,
        station_id: StationId,
        station_risk: float,
        buffer_occupancies: Dict[BufferId, int],
        buffer_capacities: Optional[Dict[BufferId, int]] = None,
    ) -> Tuple[float, float, float, List[StationId], PropagationDirection]:
        """
        Analyzes the spatial constraint propagation risks emanating from a constrained station.
        Returns:
            (upstream_blocking_risk, downstream_starvation_risk, propagation_score, affected_stations, direction)
        """
        if station_risk < 0.20:
            return 0.0, 0.0, 0.0, [], PropagationDirection.NONE

        st_idx = self.STATION_SEQUENCE.index(station_id)
        up_buf_id, down_buf_id = self.STATION_BUFFERS[station_id]
        capacities = buffer_capacities or {b: 5 for b in BufferId}

        affected_stations: List[StationId] = []
        up_blocking_risk = 0.0
        down_starvation_risk = 0.0

        # 1. Upstream Blocking Analysis (Affects S_{i-1} as upstream buffer fills)
        if st_idx > 0 and up_buf_id is not None:
            upstream_station = self.STATION_SEQUENCE[st_idx - 1]
            up_occ = buffer_occupancies.get(up_buf_id, 0)
            up_cap = max(1, capacities.get(up_buf_id, 5))
            fill_ratio = float(np.clip(up_occ / up_cap, 0.0, 1.0))

            # Upstream blocking risk scales with the station bottleneck risk and upstream buffer fill level
            up_blocking_risk = station_risk * (0.30 + 0.70 * fill_ratio)
            if up_occ >= 3 or up_blocking_risk > 0.35:
                affected_stations.append(upstream_station)

        # 2. Downstream Starvation Analysis (Affects S_{i+1} as downstream buffer drains)
        if st_idx < len(self.STATION_SEQUENCE) - 1 and down_buf_id is not None:
            downstream_station = self.STATION_SEQUENCE[st_idx + 1]
            down_occ = buffer_occupancies.get(down_buf_id, 0)
            down_cap = max(1, capacities.get(down_buf_id, 5))
            drain_ratio = float(np.clip(1.0 - (down_occ / down_cap), 0.0, 1.0))

            # Downstream starvation risk scales with station bottleneck risk and buffer emptiness
            down_starvation_risk = station_risk * (0.30 + 0.70 * drain_ratio)
            if down_occ <= 2 or down_starvation_risk > 0.35:
                affected_stations.append(downstream_station)

        propagation_score = max(up_blocking_risk, down_starvation_risk)

        # 3. Determine Propagation Direction
        if up_blocking_risk > 0.40 and down_starvation_risk > 0.40:
            direction = PropagationDirection.BIDIRECTIONAL
        elif up_blocking_risk > 0.30:
            direction = PropagationDirection.UPSTREAM_BLOCKING
        elif down_starvation_risk > 0.30:
            direction = PropagationDirection.DOWNSTREAM_STARVATION
        else:
            direction = PropagationDirection.NONE

        return (
            round(float(up_blocking_risk), 4),
            round(float(down_starvation_risk), 4),
            round(float(propagation_score), 4),
            affected_stations,
            direction,
        )
