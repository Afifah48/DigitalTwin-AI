"""
Abstract Base Class for Anomaly Detection Models.

Defines standard interface across classical baseline (Isolation Forest) and
deep learning sequence model (LSTM Autoencoder).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


class AnomalyModel(ABC):
    """Common abstraction for all anomaly detection model implementations."""

    def __init__(self, model_name: str, version: str = "1.0.0") -> None:
        self.model_name = model_name
        self.version = version
        self.is_fitted: bool = False
        self.threshold: float = 0.5
        self.feature_names: List[str] = []
        self.metadata: Dict[str, Any] = {}

    @abstractmethod
    def fit(
        self,
        X: Union[np.ndarray, List[List[float]]],
        val_X: Optional[Union[np.ndarray, List[List[float]]]] = None,
        **kwargs: Any,
    ) -> "AnomalyModel":
        """
        Fits the anomaly detection model on nominal reference data.

        Args:
            X: Training dataset features (snapshots or sequences).
            val_X: Validation dataset features (used to derive anomaly threshold).
            **kwargs: Hyperparameters or training options.
        """
        pass

    @abstractmethod
    def score_samples(self, X: Union[np.ndarray, List[List[float]]]) -> np.ndarray:
        """
        Computes continuous anomaly score for each sample.
        Higher score indicates higher degree of abnormality.

        Returns:
            1D numpy array of float anomaly scores in [0.0, 1.0].
        """
        pass

    @abstractmethod
    def predict(self, X: Union[np.ndarray, List[List[float]]]) -> np.ndarray:
        """
        Predicts binary anomaly classification (True = Anomaly, False = Normal).

        Returns:
            1D boolean numpy array.
        """
        pass

    @abstractmethod
    def get_feature_importances(
        self,
        X: Union[np.ndarray, List[List[float]]],
        top_k: int = 3,
    ) -> List[List[str]]:
        """
        Explains which features contributed most to the anomaly scores.

        Returns:
            List of lists containing top-k feature names per sample.
        """
        pass

    @abstractmethod
    def save(self, directory_path: str) -> str:
        """
        Serializes model weights and configuration to disk.

        Returns:
            Path to the saved artifact directory.
        """
        pass

    @classmethod
    @abstractmethod
    def load(cls, directory_path: str) -> "AnomalyModel":
        """Loads and restores model from saved artifact directory."""
        pass
