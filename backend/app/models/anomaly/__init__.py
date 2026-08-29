"""
Anomaly detection model package.

Exposes features, models (Isolation Forest, LSTM Autoencoder), and the AnomalyService.
"""

from backend.app.models.anomaly.features import (
    ANOMALY_FEATURE_NAMES,
    FeatureScaler,
    encode_machine_state,
    extract_station_features,
)
from backend.app.models.anomaly.isolation_forest import IsolationForestAnomalyModel
from backend.app.models.anomaly.lstm_autoencoder import (
    LSTMAutoencoderModel,
    LSTMAutoencoderNetwork,
    LSTMDecoder,
    LSTMEncoder,
)
from backend.app.models.anomaly.model import AnomalyModel
from backend.app.models.anomaly.service import AnomalyService

__all__ = [
    "ANOMALY_FEATURE_NAMES",
    "FeatureScaler",
    "encode_machine_state",
    "extract_station_features",
    "AnomalyModel",
    "IsolationForestAnomalyModel",
    "LSTMAutoencoderModel",
    "LSTMAutoencoderNetwork",
    "LSTMEncoder",
    "LSTMDecoder",
    "AnomalyService",
]
