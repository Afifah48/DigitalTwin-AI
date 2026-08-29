"""
Vehicle Quality ML Model Implementations.

Defines a common model interface (QualityModelABC) and implements:
1. Logistic Regression Baseline
2. Random Forest Baseline
3. XGBoost Classifier (Primary Model)
"""

from __future__ import annotations

import abc
import json
import os
from typing import Any, Dict, Optional, Tuple, Union
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb


class QualityModelABC(abc.ABC):
    """Abstract Base Class for Phase 6 Defect Prediction Models."""

    @abc.abstractmethod
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        val_X: Optional[np.ndarray] = None,
        val_y: Optional[np.ndarray] = None,
    ) -> QualityModelABC:
        """Fits model on feature matrix X and binary labels y."""
        pass

    @abc.abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Returns binary predictions (0 or 1)."""
        pass

    @abc.abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Returns predicted probability of defect (class 1)."""
        pass

    @abc.abstractmethod
    def save(self, filepath: str) -> None:
        """Serializes model to disk."""
        pass

    @abc.abstractmethod
    def load(self, filepath: str) -> QualityModelABC:
        """Restores model from disk."""
        pass


class LogisticRegressionQualityModel(QualityModelABC):
    """Logistic Regression Comparison Baseline with Balanced Class Weights."""

    def __init__(self, C: float = 1.0, max_iter: int = 1000, random_state: int = 42) -> None:
        self.C = C
        self.max_iter = max_iter
        self.random_state = random_state
        self.model = LogisticRegression(
            C=C,
            max_iter=max_iter,
            class_weight="balanced",
            random_state=random_state,
            solver="lbfgs",
        )
        self.is_fitted = False

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        val_X: Optional[np.ndarray] = None,
        val_y: Optional[np.ndarray] = None,
    ) -> LogisticRegressionQualityModel:
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict!")
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict_proba!")
        probs = self.model.predict_proba(X)
        return probs[:, 1]

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        joblib.dump(self, filepath)

    def load(self, filepath: str) -> LogisticRegressionQualityModel:
        loaded = joblib.load(filepath)
        self.model = loaded.model
        self.is_fitted = loaded.is_fitted
        return self


class RandomForestQualityModel(QualityModelABC):
    """Random Forest Comparison Baseline with Balanced Subsample Weights."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = 10,
        min_samples_split: int = 4,
        random_state: int = 42,
    ) -> None:
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.random_state = random_state
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            class_weight="balanced_subsample",
            random_state=random_state,
            n_jobs=-1,
        )
        self.is_fitted = False

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        val_X: Optional[np.ndarray] = None,
        val_y: Optional[np.ndarray] = None,
    ) -> RandomForestQualityModel:
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict!")
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict_proba!")
        probs = self.model.predict_proba(X)
        return probs[:, 1]

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        joblib.dump(self, filepath)

    def load(self, filepath: str) -> RandomForestQualityModel:
        loaded = joblib.load(filepath)
        self.model = loaded.model
        self.is_fitted = loaded.is_fitted
        return self


class XGBoostQualityModel(QualityModelABC):
    """
    Primary XGBoost Classifier for Vehicle Defect Prediction.

    Supports scale_pos_weight for class imbalance, early stopping on validation,
    and native SHAP TreeExplainer compatibility.
    """

    def __init__(
        self,
        n_estimators: int = 150,
        max_depth: int = 5,
        learning_rate: float = 0.05,
        subsample: float = 0.85,
        colsample_bytree: float = 0.85,
        scale_pos_weight: Optional[float] = None,
        random_state: int = 42,
    ) -> None:
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.scale_pos_weight = scale_pos_weight
        self.random_state = random_state
        self.model: Optional[xgb.XGBClassifier] = None
        self.is_fitted = False

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        val_X: Optional[np.ndarray] = None,
        val_y: Optional[np.ndarray] = None,
    ) -> XGBoostQualityModel:
        # Calculate dynamic class imbalance weight if not specified
        if self.scale_pos_weight is None:
            n_pos = np.sum(y == 1)
            n_neg = np.sum(y == 0)
            spw = float(n_neg / max(1, n_pos))
        else:
            spw = float(self.scale_pos_weight)

        self.model = xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            scale_pos_weight=spw,
            random_state=self.random_state,
            eval_metric="aucpr",
            n_jobs=-1,
        )

        if val_X is not None and val_y is not None:
            self.model.fit(
                X,
                y,
                eval_set=[(X, y), (val_X, val_y)],
                verbose=False,
            )
        else:
            self.model.fit(X, y, verbose=False)

        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model must be fitted before predict!")
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model must be fitted before predict_proba!")
        probs = self.model.predict_proba(X)
        return probs[:, 1]

    def save(self, filepath: str) -> None:
        """Saves model to JSON format (or joblib if .joblib)."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        if filepath.endswith(".json"):
            self.model.save_model(filepath)
        else:
            joblib.dump(self, filepath)

    def load(self, filepath: str) -> XGBoostQualityModel:
        """Loads model from JSON format or joblib."""
        if filepath.endswith(".json"):
            self.model = xgb.XGBClassifier()
            self.model.load_model(filepath)
            self.is_fitted = True
        else:
            loaded = joblib.load(filepath)
            self.model = loaded.model
            self.is_fitted = loaded.is_fitted
        return self
