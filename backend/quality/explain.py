
"""
SHAP TreeExplainer and Feature Attribution Module.

Calculates exact, model-agnostic feature attributions for vehicle defect predictions,
identifying the top contributing factors that increase or decrease risk.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from backend.quality.schemas import TopRiskFactor


class QualityExplainer:
    """
    SHAP-based feature attribution generator for Phase 6 quality models.
    """

    def __init__(
        self,
        model: Any,
        feature_names: List[str],
        background_data: Optional[np.ndarray] = None,
    ) -> None:
        self.model = model
        self.feature_names = feature_names
        self.explainer: Optional[Any] = None
        self._init_explainer(model, background_data)

    def _init_explainer(
        self,
        model: Any,
        background_data: Optional[np.ndarray],
    ) -> None:
        # Import SHAP only when the explainer is actually initialized.
        # This prevents SHAP and its large dependency tree from loading
        # when the API starts.
        try:
            import shap
        except ImportError:
            self.explainer = None
            return

        # Check if underlying model is an XGBoost or Tree ensemble
        raw_estimator = getattr(model, "model", model)

        try:
            self.explainer = shap.TreeExplainer(raw_estimator)

        except Exception:
            # Fallback to general explainer if non-tree model
            if background_data is not None:
                bg = background_data[:50]

                predict_fn = getattr(
                    model,
                    "predict_proba",
                    raw_estimator.predict_proba,
                )

                try:
                    self.explainer = shap.Explainer(
                        predict_fn,
                        bg,
                    )
                except Exception:
                    self.explainer = None

            else:
                self.explainer = None

    def explain_instance(
        self,
        features_array: np.ndarray,
        raw_feature_dict: Optional[Dict[str, float]] = None,
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Computes SHAP feature attribution for a single vehicle feature vector.

        Returns top_k factors with feature name, contribution, direction,
        and actual value.
        """

        arr = np.asarray(features_array, dtype=np.float32)

        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        if self.explainer is None:
            # Heuristic attribution fallback if explainer initialization failed
            return self._heuristic_attribution(
                arr[0],
                raw_feature_dict,
                top_k,
            )

        try:
            shap_values = self.explainer(arr)

            # Handle different SHAP output shapes
            if hasattr(shap_values, "values"):
                sv = shap_values.values
            else:
                sv = np.asarray(shap_values)

            # If classification with 2 outputs (class 0, class 1)
            if sv.ndim == 3:
                vals = sv[0, :, 1]

            elif sv.ndim == 2:
                vals = sv[0]

            else:
                vals = sv

            # Rank by absolute contribution
            ranked_indices = np.argsort(-np.abs(vals))

            factors: List[Dict[str, Any]] = []

            for idx in ranked_indices[:top_k]:
                feat_name = (
                    self.feature_names[idx]
                    if idx < len(self.feature_names)
                    else f"feature_{idx}"
                )

                contrib = float(vals[idx])

                direction = (
                    "INCREASES_DEFECT_RISK"
                    if contrib > 0
                    else "DECREASES_DEFECT_RISK"
                )

                f_val = (
                    raw_feature_dict.get(
                        feat_name,
                        float(arr[0, idx]),
                    )
                    if raw_feature_dict
                    else float(arr[0, idx])
                )

                factors.append(
                    TopRiskFactor(
                        feature=feat_name,
                        contribution=contrib,
                        direction=direction,
                        feature_value=f_val,
                    ).to_dict()
                )

            return factors

        except Exception:
            return self._heuristic_attribution(
                arr[0],
                raw_feature_dict,
                top_k,
            )

    def _heuristic_attribution(
        self,
        feature_vector: np.ndarray,
        raw_feature_dict: Optional[Dict[str, float]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Statistical fallback ranking features by magnitude."""

        ranked_indices = np.argsort(-np.abs(feature_vector))

        factors: List[Dict[str, Any]] = []

        for idx in ranked_indices[:top_k]:
            feat_name = (
                self.feature_names[idx]
                if idx < len(self.feature_names)
                else f"feature_{idx}"
            )

            val = float(feature_vector[idx])

            direction = (
                "INCREASES_DEFECT_RISK"
                if val > 0
                else "DECREASES_DEFECT_RISK"
            )

            f_val = (
                raw_feature_dict.get(feat_name, val)
                if raw_feature_dict
                else val
            )

            factors.append(
                TopRiskFactor(
                    feature=feat_name,
                    contribution=val * 0.1,
                    direction=direction,
                    feature_value=f_val,
                ).to_dict()
            )

        return factors
