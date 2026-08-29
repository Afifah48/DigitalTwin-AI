"""
Model B: PyTorch LSTM Sequence Autoencoder Anomaly Detector.

Reconstructs rolling multi-sensor telemetry sequences and flags reconstruction
errors as temporal process degradation anomalies.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from backend.app.models.anomaly.features import ANOMALY_FEATURE_NAMES
from backend.app.models.anomaly.model import AnomalyModel


class LSTMEncoder(nn.Module):
    """Encodes multi-variate time-series sequence into a compact latent vector."""

    def __init__(
        self,
        input_dim: int = 11,
        hidden_dim: int = 32,
        num_layers: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch_size, window_size, input_dim)
        _, (hn, _) = self.lstm(x)
        # hn[-1]: (batch_size, hidden_dim) - final layer hidden state
        return hn[-1]


class LSTMDecoder(nn.Module):
    """Reconstructs sequence from the latent vector."""

    def __init__(
        self,
        latent_dim: int = 32,
        hidden_dim: int = 32,
        output_dim: int = 11,
        window_size: int = 15,
        num_layers: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.window_size = window_size
        self.lstm = nn.LSTM(
            input_size=latent_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.output_layer = nn.Linear(hidden_dim, output_dim)

    def forward(self, latent: torch.Tensor, seq_len: Optional[int] = None) -> torch.Tensor:
        # latent: (batch_size, latent_dim) -> repeat across target sequence length
        batch_size = latent.size(0)
        target_len = seq_len or self.window_size
        repeated = latent.unsqueeze(1).repeat(1, target_len, 1)
        # repeated: (batch_size, target_len, latent_dim)
        lstm_out, _ = self.lstm(repeated)
        # lstm_out: (batch_size, target_len, hidden_dim)
        reconstruction = self.output_layer(lstm_out)
        # reconstruction: (batch_size, target_len, output_dim)
        return reconstruction


class LSTMAutoencoderNetwork(nn.Module):
    """Complete Sequence Autoencoder Network."""

    def __init__(
        self,
        input_dim: int = 11,
        hidden_dim: int = 32,
        window_size: int = 15,
        num_layers: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.encoder = LSTMEncoder(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_layers=num_layers,
            dropout=dropout,
        )
        self.decoder = LSTMDecoder(
            latent_dim=hidden_dim,
            hidden_dim=hidden_dim,
            output_dim=input_dim,
            window_size=window_size,
            num_layers=num_layers,
            dropout=dropout,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        seq_len = x.size(1)
        latent = self.encoder(x)
        reconstructed = self.decoder(latent, seq_len=seq_len)
        return reconstructed


class LSTMAutoencoderModel(AnomalyModel):
    """
    LSTM Autoencoder model implementing the AnomalyModel lifecycle.

    Trained by minimizing Mean Squared Reconstruction Error on nominal operating sequences.
    """

    def __init__(
        self,
        window_size: int = 15,
        input_dim: int = 11,
        hidden_dim: int = 32,
        num_layers: int = 2,
        dropout: float = 0.1,
        learning_rate: float = 1e-3,
        batch_size: int = 32,
        epochs: int = 25,
        random_state: int = 42,
        version: str = "1.0.0",
        device: Optional[str] = None,
    ) -> None:
        super().__init__(model_name="lstm_autoencoder", version=version)
        self.window_size = window_size
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.random_state = random_state
        self.feature_names = list(ANOMALY_FEATURE_NAMES)

        if device:
            self.device = torch.device(device)
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Set reproducible seeds
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        self.network: LSTMAutoencoderNetwork = LSTMAutoencoderNetwork(
            input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
            window_size=self.window_size,
            num_layers=self.num_layers,
            dropout=self.dropout,
        ).to(self.device)

        self.val_error_mean: float = 0.0
        self.val_error_std: float = 1.0
        self.val_error_p99: float = 0.5

    def fit(
        self,
        X: Union[np.ndarray, List[List[List[float]]]],
        val_X: Optional[Union[np.ndarray, List[List[List[float]]]]] = None,
        epochs: Optional[int] = None,
        verbose: bool = False,
        **kwargs: Any,
    ) -> "LSTMAutoencoderModel":
        """
        Trains the autoencoder on nominal sequence windows.

        Args:
            X: Training array of shape (N_samples, window_size, input_dim)
            val_X: Validation array of nominal sequences for threshold derivation.
        """
        train_data = np.asarray(X, dtype=np.float32)
        if train_data.ndim != 3 or train_data.shape[1] != self.window_size:
            raise ValueError(
                f"Expected 3D array (N, {self.window_size}, {self.input_dim}), got {train_data.shape}"
            )

        n_epochs = epochs or self.epochs
        dataset = TensorDataset(torch.tensor(train_data, dtype=torch.float32))
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

        optimizer = torch.optim.Adam(self.network.parameters(), lr=self.learning_rate)
        criterion = nn.MSELoss()

        self.network.train()
        for ep in range(n_epochs):
            total_loss = 0.0
            for (batch_x,) in loader:
                batch_x = batch_x.to(self.device)
                optimizer.zero_grad()
                reconstructed = self.network(batch_x)
                loss = criterion(reconstructed, batch_x)
                loss.backward()
                optimizer.step()
                total_loss += loss.item() * batch_x.size(0)

            if verbose and (ep + 1) % 5 == 0:
                avg_loss = total_loss / len(train_data)
                print(f"[LSTM Autoencoder] Epoch {ep+1}/{n_epochs} - Loss: {avg_loss:.6f}")

        self.is_fitted = True

        # Compute validation error distribution for statistical threshold derivation
        val_data = np.asarray(val_X, dtype=np.float32) if val_X is not None else train_data
        raw_val_errors = self._compute_raw_reconstruction_errors(val_data)

        self.val_error_mean = float(np.mean(raw_val_errors))
        self.val_error_std = float(np.std(raw_val_errors))
        self.val_error_p99 = float(np.percentile(raw_val_errors, 99.0))

        # Statistically derived threshold: 99th percentile of nominal errors
        self.threshold = round(self.val_error_p99, 5)

        self.metadata = {
            "model_name": self.model_name,
            "version": self.version,
            "window_size": self.window_size,
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "num_layers": self.num_layers,
            "epochs": n_epochs,
            "threshold": self.threshold,
            "threshold_method": "99th_percentile_nominal_validation",
            "val_error_mean": round(self.val_error_mean, 5),
            "val_error_std": round(self.val_error_std, 5),
            "val_error_p99": round(self.val_error_p99, 5),
            "feature_names": self.feature_names,
            "random_state": self.random_state,
        }
        return self

    def _compute_raw_reconstruction_errors(self, X: np.ndarray) -> np.ndarray:
        """Calculates raw sample-wise MSE reconstruction errors across all features and timesteps."""
        self.network.eval()
        with torch.no_grad():
            tensor_x = torch.tensor(X, dtype=torch.float32).to(self.device)
            reconstructed = self.network(tensor_x)
            # MSE per sample across (window_size, input_dim)
            diff = (tensor_x - reconstructed).cpu().numpy()
            mse_per_sample = np.mean(diff ** 2, axis=(1, 2))
        return mse_per_sample

    def predict_detailed(
        self,
        X: Union[np.ndarray, List[List[List[float]]]],
        top_k: int = 3,
    ) -> Tuple[np.ndarray, np.ndarray, List[List[str]]]:
        """
        Computes anomaly_scores, detected boolean mask, and top_signals in a single forward pass.
        """
        data = np.asarray(X, dtype=np.float32)
        self.network.eval()
        with torch.no_grad():
            tensor_x = torch.tensor(data, dtype=torch.float32).to(self.device)
            reconstructed = self.network(tensor_x)
            diff = (tensor_x - reconstructed).cpu().numpy()
            raw_errors = np.mean(diff ** 2, axis=(1, 2))
            feature_mse = np.mean(diff ** 2, axis=1)

        safe_scale = max(self.threshold * 1.5, 1e-4)
        anomaly_scores = np.clip(np.tanh(raw_errors / safe_scale), 0.0, 1.0)
        detected = raw_errors >= self.threshold

        top_signals: List[List[str]] = []
        for row in feature_mse:
            top_indices = np.argsort(row)[::-1][:top_k]
            top_signals.append([self.feature_names[i] for i in top_indices])

        return anomaly_scores, detected, top_signals

    def score_samples(self, X: Union[np.ndarray, List[List[List[float]]]]) -> np.ndarray:
        """
        Computes continuous anomaly score normalized in [0.0, 1.0].
        Formula: score = tanh(raw_error / (1.5 * threshold)).
        """
        if not self.is_fitted:
            raise RuntimeError("LSTM Autoencoder model is not fitted.")
        data = np.asarray(X, dtype=np.float32)
        raw_errors = self._compute_raw_reconstruction_errors(data)
        safe_scale = max(self.threshold * 1.5, 1e-4)
        normalized = np.tanh(raw_errors / safe_scale)
        return np.clip(normalized, 0.0, 1.0)

    def predict(self, X: Union[np.ndarray, List[List[List[float]]]]) -> np.ndarray:
        """Returns boolean anomaly mask (True if raw reconstruction error >= threshold)."""
        if not self.is_fitted:
            raise RuntimeError("LSTM Autoencoder model is not fitted.")
        data = np.asarray(X, dtype=np.float32)
        raw_errors = self._compute_raw_reconstruction_errors(data)
        return raw_errors >= self.threshold

    def get_feature_importances(
        self,
        X: Union[np.ndarray, List[List[List[float]]]],
        top_k: int = 3,
    ) -> List[List[str]]:
        """
        Computes top contributing features based on feature-wise reconstruction error:
        err_f = average((x_{w,f} - x_hat_{w,f})^2)
        """
        data = np.asarray(X, dtype=np.float32)
        self.network.eval()
        with torch.no_grad():
            tensor_x = torch.tensor(data, dtype=torch.float32).to(self.device)
            reconstructed = self.network(tensor_x)
            diff = (tensor_x - reconstructed).cpu().numpy()
            # Mean error across window timesteps per feature: shape (batch_size, input_dim)
            feature_mse = np.mean(diff ** 2, axis=1)

        top_signals: List[List[str]] = []
        for row in feature_mse:
            top_indices = np.argsort(row)[::-1][:top_k]
            top_signals.append([self.feature_names[i] for i in top_indices])
        return top_signals

    def save(self, directory_path: str) -> str:
        """Saves PyTorch weights and metadata."""
        os.makedirs(directory_path, exist_ok=True)
        weights_path = os.path.join(directory_path, "lstm_autoencoder.pt")
        meta_path = os.path.join(directory_path, "lstm_autoencoder_metadata.json")

        torch.save({
            "state_dict": self.network.state_dict(),
            "config": {
                "window_size": self.window_size,
                "input_dim": self.input_dim,
                "hidden_dim": self.hidden_dim,
                "num_layers": self.num_layers,
                "dropout": self.dropout,
                "threshold": self.threshold,
                "val_error_mean": self.val_error_mean,
                "val_error_std": self.val_error_std,
                "val_error_p99": self.val_error_p99,
            },
        }, weights_path)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        return directory_path

    @classmethod
    def load(cls, directory_path: str, device: Optional[str] = None) -> "LSTMAutoencoderModel":
        """Loads model weights and metadata from saved directory."""
        weights_path = os.path.join(directory_path, "lstm_autoencoder.pt")
        meta_path = os.path.join(directory_path, "lstm_autoencoder_metadata.json")

        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        checkpoint = torch.load(weights_path, map_location="cpu")
        cfg = checkpoint["config"]

        instance = cls(
            window_size=cfg.get("window_size", 15),
            input_dim=cfg.get("input_dim", 11),
            hidden_dim=cfg.get("hidden_dim", 32),
            num_layers=cfg.get("num_layers", 2),
            dropout=cfg.get("dropout", 0.1),
            version=metadata.get("version", "1.0.0"),
            device=device,
        )

        instance.network.load_state_dict(checkpoint["state_dict"])
        instance.threshold = cfg.get("threshold", 0.5)
        instance.val_error_mean = cfg.get("val_error_mean", 0.0)
        instance.val_error_std = cfg.get("val_error_std", 1.0)
        instance.val_error_p99 = cfg.get("val_error_p99", 0.5)
        instance.metadata = metadata
        instance.is_fitted = True
        return instance
