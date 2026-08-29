"""
Anomaly Detection Service Orchestrator.

Manages feature extraction, rolling sequence buffers, scaler transformations,
model inference, lead time tracking, and prediction schema assembly.
"""

from __future__ import annotations

import collections
import os
from typing import Any, Deque, Dict, List, Optional, Tuple, Union
import numpy as np

from backend.analytics.baseline import FactoryBaseline
from backend.app.models.anomaly.features import (
    ANOMALY_FEATURE_NAMES,
    FeatureScaler,
    extract_station_features,
)
from backend.app.models.anomaly.isolation_forest import IsolationForestAnomalyModel
from backend.app.models.anomaly.lstm_autoencoder import LSTMAutoencoderModel
from backend.app.models.anomaly.model import AnomalyModel
from backend.app.schemas.anomaly import (
    AnomalyPrediction,
    BatchAnomalyPrediction,
    SeverityLevel,
    score_to_severity,
)


class AnomalyService:
    """
    Unified ML anomaly inference service.

    Maintains per-station temporal sequence buffers and provides real-time
    anomaly scoring, severity classification, and lead-time calculations.
    """

    def __init__(
        self,
        model: Optional[AnomalyModel] = None,
        scaler: Optional[FeatureScaler] = None,
        baseline: Optional[FactoryBaseline] = None,
        window_size: int = 15,
        low_severity_threshold: float = 0.30,
        high_severity_threshold: float = 0.70,
    ) -> None:
        self.scaler = scaler or FeatureScaler()
        self.baseline = baseline
        self.low_severity_threshold = low_severity_threshold
        self.high_severity_threshold = high_severity_threshold

        if model is not None and hasattr(model, "window_size"):
            self.window_size = getattr(model, "window_size")
        else:
            self.window_size = window_size

        self.model = model

        # Per-station rolling feature history buffer: station_id -> deque of normalized feature vectors
        self._history_buffers: Dict[str, Deque[np.ndarray]] = collections.defaultdict(
            lambda: collections.deque(maxlen=self.window_size)
        )

        # Track first detection timestamp per station for lead-time calculation
        self._first_detection_time: Dict[str, float] = {}

    def reset_history(self, station_id: Optional[str] = None) -> None:
        """Clears rolling historical sequence buffers and detection timestamps."""
        if station_id:
            if station_id in self._history_buffers:
                self._history_buffers[station_id].clear()
            self._first_detection_time.pop(station_id, None)
        else:
            self._history_buffers.clear()
            self._first_detection_time.clear()

    def set_baseline(self, baseline: FactoryBaseline) -> None:
        """Sets or updates the reference baseline."""
        self.baseline = baseline

    def set_model(self, model: AnomalyModel) -> None:
        """Sets active anomaly detection model (Isolation Forest or LSTM Autoencoder)."""
        self.model = model
        if hasattr(model, "window_size"):
            self.window_size = getattr(model, "window_size")
            # Recreate buffers with new maxlen
            old_buffers = dict(self._history_buffers)
            self._history_buffers = collections.defaultdict(
                lambda: collections.deque(maxlen=self.window_size)
            )
            for k, v in old_buffers.items():
                self._history_buffers[k] = collections.deque(list(v)[-self.window_size:], maxlen=self.window_size)

    def predict_station(
        self,
        station_id: str,
        station_telemetry: Dict[str, Any],
        timestamp: float,
        connected_buffer_occupancy: float = 0.0,
        ground_truth_failure_time: Optional[float] = None,
    ) -> AnomalyPrediction:
        """
        Extracts features, maintains rolling history, runs inference, and returns AnomalyPrediction.

        Args:
            station_id: Machine station identifier (e.g., 'S3').
            station_telemetry: Current sensor and operating values.
            timestamp: Simulation epoch or relative seconds.
            connected_buffer_occupancy: Immediate buffer occupancy/pressure.
            ground_truth_failure_time: Known bottleneck or breakdown timestamp (optional).

        Returns:
            Structured AnomalyPrediction object.
        """
        # Step 1: Extract 11 raw features
        st_baseline = self.baseline.get_station(station_id) if self.baseline else None
        raw_features = extract_station_features(
            station_telemetry=station_telemetry,
            station_baseline=st_baseline,
            connected_buffer_occupancy=connected_buffer_occupancy,
        )

        # Step 2: Scale features
        if self.scaler.is_fitted:
            scaled_features = self.scaler.transform(raw_features.reshape(1, -1))[0]
        else:
            scaled_features = raw_features

        # Step 3: Maintain rolling history queue
        buf = self._history_buffers[station_id]
        buf.append(scaled_features)

        # Step 4: Run Model Inference
        if self.model is None or not self.model.is_fitted:
            # Fallback if no model is loaded yet
            return AnomalyPrediction(
                station_id=station_id,
                timestamp=timestamp,
                anomaly_score=0.0,
                anomaly_probability=None,
                severity=SeverityLevel.LOW.value,
                detected=False,
                top_signals=[],
                metadata={"status": "no_model_fitted"},
            )

        is_warming_up = len(buf) < self.window_size

        if isinstance(self.model, LSTMAutoencoderModel):
            # Model B: Sequence Model
            # If buffer is not yet full, pad by repeating earliest available observation
            seq_list = list(buf)
            while len(seq_list) < self.window_size:
                seq_list.insert(0, seq_list[0])
            seq_array = np.array([seq_list], dtype=np.float32)  # shape (1, window_size, 11)

            scores, preds, top_sigs_list = self.model.predict_detailed(seq_array, top_k=3)
            anomaly_score = float(scores[0])
            if is_warming_up:
                anomaly_score = min(anomaly_score, 0.25)
                detected = False
            else:
                detected = bool(preds[0])
            top_sigs = top_sigs_list[0]
        else:
            # Model A: Isolation Forest Snapshot Model
            snapshot_array = scaled_features.reshape(1, -1)
            scores, preds, top_sigs_list = self.model.predict_detailed(snapshot_array, top_k=3)
            anomaly_score = float(scores[0])
            detected = bool(preds[0])
            top_sigs = top_sigs_list[0]

        # Step 5: Severity & Lead-Time Calculation
        severity = score_to_severity(
            anomaly_score,
            low_threshold=self.low_severity_threshold,
            high_threshold=self.high_severity_threshold,
        ).value

        lead_time: Optional[float] = None
        if detected:
            if station_id not in self._first_detection_time:
                self._first_detection_time[station_id] = timestamp

            if ground_truth_failure_time is not None:
                first_t = self._first_detection_time[station_id]
                lead_time = max(0.0, ground_truth_failure_time - first_t)

        return AnomalyPrediction(
            station_id=station_id,
            timestamp=timestamp,
            anomaly_score=round(anomaly_score, 4),
            anomaly_probability=None,  # Uncalibrated raw probability is not fabricated
            severity=severity,
            detected=detected,
            lead_time_if_known=round(lead_time, 2) if lead_time is not None else None,
            top_signals=top_sigs,
            metadata={
                "model_name": self.model.model_name,
                "model_version": self.model.version,
                "threshold": self.model.threshold,
                "window_size": self.window_size,
            },
        )

    def predict_factory_snapshot(
        self,
        factory_state: Dict[str, Any],
        ground_truth_events: Optional[Dict[str, float]] = None,
    ) -> BatchAnomalyPrediction:
        """
        Runs anomaly detection across all stations present in the factory snapshot.
        """
        timestamp = float(factory_state.get("timestamp", 0.0))
        raw_stations = factory_state.get("stations", {})
        raw_buffers = factory_state.get("buffers", {})

        predictions: Dict[str, AnomalyPrediction] = {}
        anomalous_st: List[str] = []
        max_score = -1.0
        highest_station: Optional[str] = None

        # Build buffer occupancy lookup
        buf_map: Dict[str, float] = {}
        for buf_id, buf_info in raw_buffers.items():
            if isinstance(buf_info, dict):
                buf_map[buf_id] = float(buf_info.get("occupancy", 0.0))
            else:
                buf_map[buf_id] = float(buf_info)

        gt_events = ground_truth_events or {}

        for st_id, st_telemetry in sorted(raw_stations.items()):
            if not isinstance(st_telemetry, dict):
                continue
            # Associate connected buffer (e.g., B1 with S1/S2)
            connected_occ = 0.0
            for b_id, occ in buf_map.items():
                if st_id in b_id:
                    connected_occ = max(connected_occ, occ)

            gt_fail = gt_events.get(st_id)
            pred = self.predict_station(
                station_id=st_id,
                station_telemetry=st_telemetry,
                timestamp=timestamp,
                connected_buffer_occupancy=connected_occ,
                ground_truth_failure_time=gt_fail,
            )

            predictions[st_id] = pred
            if pred.detected:
                anomalous_st.append(st_id)

            if pred.anomaly_score > max_score:
                max_score = pred.anomaly_score
                highest_station = st_id

        return BatchAnomalyPrediction(
            timestamp=timestamp,
            predictions=predictions,
            anomalous_stations=anomalous_st,
            highest_anomaly_station=highest_station,
            max_anomaly_score=max_score,
        )

    def load_artifacts(self, artifact_directory: str, preferred_model: str = "lstm") -> None:
        """
        Loads saved scaler, metadata, and preferred model from disk.
        """
        scaler_path = os.path.join(artifact_directory, "scaler.json")
        if os.path.exists(scaler_path):
            self.scaler = FeatureScaler.load(scaler_path)

        if preferred_model == "lstm":
            lstm_path = os.path.join(artifact_directory, "lstm_autoencoder.pt")
            if os.path.exists(lstm_path):
                lstm_model = LSTMAutoencoderModel.load(artifact_directory)
                self.set_model(lstm_model)
        else:
            if_path = os.path.join(artifact_directory, "isolation_forest.joblib")
            if os.path.exists(if_path):
                if_model = IsolationForestAnomalyModel.load(artifact_directory)
                self.set_model(if_model)
