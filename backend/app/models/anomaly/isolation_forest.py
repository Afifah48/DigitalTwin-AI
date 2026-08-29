"""
Model A: Isolation Forest Baseline Anomaly Detector.

Implements unsupervised tree-based anomaly detection for static feature snapshots.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence, Union
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from backend.app.models.anomaly.features import ANOMALY_FEATURE_NAMES
from backend.app.models.anomaly.model import AnomalyModel


class IsolationForestAnomalyModel(AnomalyModel):
    """
    Isolation Forest anomaly detector wrapping scikit-learn's IsolationForest.

    Learns normal feature subspace partitions and scores deviations based on tree isolation depth.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        contamination: float = 0.01,
        random_state: int = 42,
        version: str = "1.0.0",
    ) -> None:
        super().__init__(model_name="isolation_forest", version=version)
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state
        self.feature_names = list(ANOMALY_FEATURE_NAMES)

        self.model: Optional[IsolationForest] = None
        self.val_score_min: float = 0.0
        self.val_score_max: float = 1.0
        self.nominal_feature_means: Optional[np.ndarray] = None
        self.nominal_feature_stds: Optional[np.ndarray] = None

    def fit(
        self,
        X: Union[np.ndarray, List[List[float]]],
        val_X: Optional[Union[np.ndarray, List[List[float]]]] = None,
        **kwargs: Any,
    ) -> "IsolationForestAnomalyModel":
        """
        Trains Isolation Forest on nominal training data and calibrates threshold on validation data.
        """
        data = np.asarray(X, dtype=np.float32)
        if data.ndim != 2:
            raise ValueError(f"Expected 2D array for Isolation Forest, got {data.shape}")

        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self.model.fit(data)
        self.is_fitted = True

        # Store training feature distribution for explainability
        self.nominal_feature_means = np.mean(data, axis=0)
        self.nominal_feature_stds = np.std(data, axis=0)
        self.nominal_feature_stds = np.where(
            self.nominal_feature_stds < 1e-4, 1.0, self.nominal_feature_stds
        )

        # Calibrate threshold on nominal validation set (or training set fallback)
        eval_data = np.asarray(val_X, dtype=np.float32) if val_X is not None else data
        raw_scores = -self.model.decision_function(eval_data)
        self.val_score_min = float(np.min(raw_scores))
        self.val_score_max = float(np.max(raw_scores))

        # Calculate calibrated scores in [0.0, 1.0]
        norm_scores = self._normalize_raw_scores(raw_scores)
        # Derive threshold as 99th percentile of nominal errors
        self.threshold = float(np.percentile(norm_scores, 99.0))

        self.metadata = {
            "model_name": self.model_name,
            "version": self.version,
            "n_estimators": self.n_estimators,
            "contamination": self.contamination,
            "random_state": self.random_state,
            "threshold": round(self.threshold, 4),
            "feature_names": self.feature_names,
            "val_score_min": self.val_score_min,
            "val_score_max": self.val_score_max,
        }
        return self

    def _normalize_raw_scores(self, raw_scores: np.ndarray) -> np.ndarray:
        """Transforms decision function score into continuous [0.0, 1.0] score."""
        # raw_scores = -decision_function. Higher is more anomalous.
        # Use a smooth sigmoid-like calibration with baseline reference
        centered = raw_scores - self.val_score_min
        spread = max(self.val_score_max - self.val_score_min, 1e-4)
        scaled = centered / spread
        # Sigmoid squash around the nominal upper range
        normalized = 1.0 / (1.0 + np.exp(-4.0 * (scaled - 0.75)))
        return np.clip(normalized, 0.0, 1.0)

    def score_samples(self, X: Union[np.ndarray, List[List[float]]]) -> np.ndarray:
        """Calculates normalized anomaly scores in [0.0, 1.0]."""
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Isolation Forest model is not fitted.")
        data = np.asarray(X, dtype=np.float32)
        raw = -self.model.decision_function(data)
        return self._normalize_raw_scores(raw)

    def predict(self, X: Union[np.ndarray, List[List[float]]]) -> np.ndarray:
        """Returns boolean anomaly mask (True if score >= threshold)."""
        scores = self.score_samples(X)
        return scores >= self.threshold

    def predict_detailed(
        self,
        X: Union[np.ndarray, List[List[float]]],
        top_k: int = 3,
    ) -> Tuple[np.ndarray, np.ndarray, List[List[str]]]:
        """
        Computes anomaly_scores, detected boolean mask, and top_signals in a single pass.
        """
        scores = self.score_samples(X)
        detected = scores >= self.threshold
        top_sigs = self.get_feature_importances(X, top_k=top_k)
        return scores, detected, top_sigs

    def get_feature_importances(
        self,
        X: Union[np.ndarray, List[List[float]]],
        top_k: int = 3,
    ) -> List[List[str]]:
        """
        Calculates top contributing features to the anomaly using z-score distance
        from nominal training means.
        """
        data = np.asarray(X, dtype=np.float32)
        if self.nominal_feature_means is None or self.nominal_feature_stds is None:
            return [self.feature_names[:top_k] for _ in range(len(data))]

        z_diffs = np.abs(data - self.nominal_feature_means) / self.nominal_feature_stds
        top_signals: List[List[str]] = []
        for row in z_diffs:
            top_indices = np.argsort(row)[::-1][:top_k]
            top_signals.append([self.feature_names[i] for i in top_indices])
        return top_signals

    def save(self, directory_path: str) -> str:
        """Saves model weights, scaler stats, and metadata."""
        os.makedirs(directory_path, exist_ok=True)
        model_path = os.path.join(directory_path, "isolation_forest.joblib")
        meta_path = os.path.join(directory_path, "isolation_forest_metadata.json")

        joblib.dump({
            "model": self.model,
            "nominal_means": self.nominal_feature_means,
            "nominal_stds": self.nominal_feature_stds,
            "val_score_min": self.val_score_min,
            "val_score_max": self.val_score_max,
            "threshold": self.threshold,
        }, model_path)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        return directory_path

    @classmethod
    def load(cls, directory_path: str) -> "IsolationForestAnomalyModel":
        """Loads model weights and metadata from directory."""
        model_path = os.path.join(directory_path, "isolation_forest.joblib")
        meta_path = os.path.join(directory_path, "isolation_forest_metadata.json")

        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        instance = cls(
            n_estimators=metadata.get("n_estimators", 100),
            contamination=metadata.get("contamination", 0.01),
            random_state=metadata.get("random_state", 42),
            version=metadata.get("version", "1.0.0"),
        )

        state = joblib.load(model_path)
        instance.model = state["model"]
        instance.nominal_feature_means = state["nominal_means"]
        instance.nominal_feature_stds = state["nominal_stds"]
        instance.val_score_min = state["val_score_min"]
        instance.val_score_max = state["val_score_max"]
        instance.threshold = state["threshold"]
        instance.metadata = metadata
        instance.is_fitted = True
        return instance
