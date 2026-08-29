"""
Quality Risk Service Orchestrator.

Maintains the end-to-end inference pipeline for vehicle defect prediction:
Temporal Filtering -> Phase 4/5 Adapters -> Feature Extraction -> Preprocessor ->
Model Inference -> Probability Calibration -> Operational Risk Policy -> SHAP Attribution -> VehicleRiskPrediction.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np

from backend.quality.calibration import QualityProbabilityCalibrator
from backend.quality.explain import QualityExplainer
from backend.quality.features import (
    QUALITY_FEATURE_NAMES,
    VehicleFeaturePreprocessor,
    extract_vehicle_features,
    feature_dict_to_array,
)
from backend.quality.models import (
    LogisticRegressionQualityModel,
    QualityModelABC,
    RandomForestQualityModel,
    XGBoostQualityModel,
)
from backend.quality.phase4_adapter import Phase4Adapter
from backend.quality.phase5_adapter import Phase5Adapter
from backend.quality.risk import (
    DEFAULT_RISK_POLICY,
    QualityRiskPolicy,
    compute_vehicle_risk,
)
from backend.quality.schemas import (
    VehicleObservation,
    VehicleRiskPrediction,
)
from backend.quality.temporal import validate_zero_leakage


class QualityRiskService:
    """
    Production-grade Vehicle Defect & Quality Risk Prediction Service.
    """

    def __init__(
        self,
        model: Optional[QualityModelABC] = None,
        preprocessor: Optional[VehicleFeaturePreprocessor] = None,
        calibrator: Optional[QualityProbabilityCalibrator] = None,
        phase4_adapter: Optional[Phase4Adapter] = None,
        phase5_adapter: Optional[Phase5Adapter] = None,
        risk_policy: Optional[QualityRiskPolicy] = None,
        model_name: str = "xgboost",
        model_version: str = "1.0.0",
    ) -> None:
        self.model = model
        self.preprocessor = preprocessor or VehicleFeaturePreprocessor()
        self.calibrator = calibrator
        self.phase4_adapter = phase4_adapter or Phase4Adapter()
        self.phase5_adapter = phase5_adapter or Phase5Adapter()
        self.risk_policy = risk_policy or DEFAULT_RISK_POLICY
        self.model_name = model_name
        self.model_version = model_version
        self.explainer: Optional[QualityExplainer] = None
        self.feature_names: List[str] = list(QUALITY_FEATURE_NAMES)

        if self.model is not None:
            self.explainer = QualityExplainer(self.model, self.feature_names)

    def load_artifacts(self, models_dir: str, model_type: str = "xgboost") -> QualityRiskService:
        """
        Loads all required model, preprocessor, and calibration artifacts from disk.
        """
        models_path = os.path.abspath(models_dir)

        # 1. Feature Schema
        schema_path = os.path.join(models_path, "feature_schema.json")
        if os.path.exists(schema_path):
            with open(schema_path, "r") as f:
                s_data = json.load(f)
                self.feature_names = s_data.get("feature_names", list(QUALITY_FEATURE_NAMES))

        # 2. Preprocessor
        prep_path = os.path.join(models_path, "preprocessor.joblib")
        if os.path.exists(prep_path):
            self.preprocessor = VehicleFeaturePreprocessor.load(prep_path)
            self.feature_names = self.preprocessor.feature_names

        # 3. Model
        if model_type == "xgboost":
            xgb_json = os.path.join(models_path, "xgboost_model.json")
            xgb_joblib = os.path.join(models_path, "xgboost_model.joblib")
            if os.path.exists(xgb_json):
                self.model = XGBoostQualityModel().load(xgb_json)
            elif os.path.exists(xgb_joblib):
                self.model = XGBoostQualityModel().load(xgb_joblib)
            self.model_name = "xgboost"
        elif model_type == "random_forest":
            rf_path = os.path.join(models_path, "random_forest.joblib")
            if os.path.exists(rf_path):
                self.model = RandomForestQualityModel().load(rf_path)
            self.model_name = "random_forest"
        elif model_type == "logistic_regression":
            lr_path = os.path.join(models_path, "logistic_regression.joblib")
            if os.path.exists(lr_path):
                self.model = LogisticRegressionQualityModel().load(lr_path)
            self.model_name = "logistic_regression"

        # 4. Calibrator
        cal_path = os.path.join(models_path, "calibrator.joblib")
        if os.path.exists(cal_path):
            self.calibrator = QualityProbabilityCalibrator.load(cal_path)

        # 5. Metadata
        meta_path = os.path.join(models_path, "metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                meta = json.load(f)
                self.model_version = meta.get("model_version", "1.0.0")

        if self.model is not None:
            self.explainer = QualityExplainer(self.model, self.feature_names)

        return self

    def predict(
        self,
        vehicle_id: str,
        vehicle_history: Sequence[Union[VehicleObservation, Dict[str, Any]]],
        as_of_timestamp: float,
        phase4_adapter: Optional[Phase4Adapter] = None,
        phase5_adapter: Optional[Phase5Adapter] = None,
    ) -> VehicleRiskPrediction:
        """
        Executes zero-leakage prediction for an individual vehicle at `as_of_timestamp`.
        """
        p4 = phase4_adapter or self.phase4_adapter
        p5 = phase5_adapter or self.phase5_adapter

        # 1. Feature Extraction (includes strict temporal filtering)
        raw_features = extract_vehicle_features(
            vehicle_id=vehicle_id,
            vehicle_history=vehicle_history,
            as_of_timestamp=as_of_timestamp,
            phase4_adapter=p4,
            phase5_adapter=p5,
        )

        # 2. Vectorization in Canonical Schema Order
        feat_vector = feature_dict_to_array(raw_features, self.feature_names)

        # 3. Preprocessing (Standard Scaling)
        if self.preprocessor.is_fitted:
            scaled_vector = self.preprocessor.transform(feat_vector)
        else:
            scaled_vector = feat_vector.reshape(1, -1)

        # 4. Model Inference
        if self.model is not None:
            raw_prob = float(self.model.predict_proba(scaled_vector)[0])
        else:
            # Fallback based on raw anomaly scores
            raw_prob = float(raw_features.get("phase4_anomaly_score_max", 0.1))

        # 5. Probability Calibration
        if self.calibrator is not None and self.calibrator.is_fitted:
            calibrated_prob = float(self.calibrator.calibrate(np.array([raw_prob]))[0])
        else:
            calibrated_prob = raw_prob

        # Bound probability strictly in [0.0, 1.0]
        calibrated_prob = float(min(1.0, max(0.0, calibrated_prob)))

        # 6. Operational Risk Scoring & Actions
        risk_score, exposure, action = compute_vehicle_risk(
            defect_probability=calibrated_prob,
            policy=self.risk_policy,
        )

        # 7. SHAP Feature Attribution
        if self.explainer is not None:
            top_factors = self.explainer.explain_instance(
                features_array=scaled_vector,
                raw_feature_dict=raw_features,
                top_k=4,
            )
        else:
            top_factors = []

        # 8. Prediction Contract Assembly
        prediction = VehicleRiskPrediction(
            vehicle_id=vehicle_id,
            timestamp=as_of_timestamp,
            risk_score=risk_score,
            defect_probability=calibrated_prob,
            quality_exposure=exposure,
            recommended_action=action,
            top_risk_factors=top_factors,
            metadata={
                "model_name": self.model_name,
                "model_version": self.model_version,
                "raw_probability": round(raw_prob, 4),
                "is_calibrated": bool(self.calibrator and self.calibrator.is_fitted),
                "as_of_timestamp": as_of_timestamp,
            },
        )

        return prediction
