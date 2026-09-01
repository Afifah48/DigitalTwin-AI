
"""
Probability Calibration Module for Vehicle Defect Predictions.

Applies Isotonic Regression or Platt Scaling to convert raw classification scores
into statistically calibrated defect probabilities.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import joblib
import numpy as np


def calculate_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> Dict[str, float]:
    """
    Computes Expected Calibration Error (ECE), Maximum Calibration Error (MCE),
    Brier Score, and Log Loss.
    """

    # Import sklearn only when this function is actually called.
    from sklearn.calibration import calibration_curve
    from sklearn.metrics import brier_score_loss, log_loss

    y_t = np.asarray(y_true, dtype=int)
    y_p = np.clip(
        np.asarray(y_prob, dtype=float),
        1e-6,
        1.0 - 1e-6,
    )

    prob_true, prob_pred = calibration_curve(
        y_t,
        y_p,
        n_bins=n_bins,
        strategy="uniform",
    )

    # Expected Calibration Error (ECE)
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)

    bin_indices = np.digitize(
        y_p,
        bin_edges,
    ) - 1

    bin_indices = np.clip(
        bin_indices,
        0,
        n_bins - 1,
    )

    ece = 0.0
    mce = 0.0
    total_samples = len(y_t)

    for i in range(n_bins):
        bin_mask = bin_indices == i
        bin_count = np.sum(bin_mask)

        if bin_count > 0:
            bin_acc = np.mean(y_t[bin_mask])
            bin_conf = np.mean(y_p[bin_mask])
            abs_diff = abs(bin_acc - bin_conf)

            ece += (
                bin_count / total_samples
            ) * abs_diff

            mce = max(
                mce,
                abs_diff,
            )

    brier = float(
        brier_score_loss(
            y_t,
            y_p,
        )
    )

    logloss = float(
        log_loss(
            y_t,
            y_p,
        )
    )

    return {
        "expected_calibration_error": round(
            float(ece),
            4,
        ),
        "max_calibration_error": round(
            float(mce),
            4,
        ),
        "brier_score": round(
            brier,
            4,
        ),
        "log_loss": round(
            logloss,
            4,
        ),
    }


class QualityProbabilityCalibrator:
    """
    Wraps a fitted calibrator to produce calibrated probabilities.
    """

    def __init__(
        self,
        method: str = "isotonic",
    ) -> None:
        self.method = method
        self.calibrator: Optional[Any] = None
        self.is_fitted = False

    def fit(
        self,
        base_estimator: Any,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> QualityProbabilityCalibrator:
        """
        Fits calibration model on validation predictions.
        """

        # Import sklearn only when calibration is actually fitted.
        from sklearn.isotonic import IsotonicRegression
        from sklearn.linear_model import LogisticRegression

        raw_probs = base_estimator.predict_proba(
            X_val
        )

        if raw_probs.ndim == 2:
            raw_probs = raw_probs[:, 1]

        if self.method == "isotonic":
            self.calibrator = IsotonicRegression(
                out_of_bounds="clip",
                y_min=0.0,
                y_max=1.0,
            )

            self.calibrator.fit(
                raw_probs,
                y_val,
            )

        elif self.method == "sigmoid":
            # Platt scaling
            self.calibrator = LogisticRegression(
                C=1.0,
                solver="lbfgs",
            )

            self.calibrator.fit(
                raw_probs.reshape(-1, 1),
                y_val,
            )

        else:
            raise ValueError(
                f"Unknown calibration method: {self.method}"
            )

        self.is_fitted = True

        return self

    def calibrate(
        self,
        raw_probs: np.ndarray,
    ) -> np.ndarray:
        """Applies calibration mapping to raw probabilities."""

        if (
            not self.is_fitted
            or self.calibrator is None
        ):
            return np.clip(
                raw_probs,
                0.0,
                1.0,
            )

        probs_arr = np.asarray(
            raw_probs,
            dtype=float,
        )

        if self.method == "isotonic":
            return np.clip(
                self.calibrator.predict(
                    probs_arr
                ),
                0.0,
                1.0,
            )

        elif self.method == "sigmoid":
            return self.calibrator.predict_proba(
                probs_arr.reshape(-1, 1)
            )[:, 1]

        return probs_arr

    def save(
        self,
        filepath: str,
    ) -> None:
        os.makedirs(
            os.path.dirname(
                os.path.abspath(filepath)
            ),
            exist_ok=True,
        )

        joblib.dump(
            self,
            filepath,
        )

    @classmethod
    def load(
        cls,
        filepath: str,
    ) -> QualityProbabilityCalibrator:
        return joblib.load(filepath)