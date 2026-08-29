"""
Phase 6: Vehicle Quality and Defect Prediction Subsystem.
"""

from backend.quality.schemas import (
    DefectSeverity,
    QualityExposureLevel,
    RecommendedAction,
    TopRiskFactor,
    VehicleDefectGroundTruth,
    VehicleObservation,
    VehicleRiskPrediction,
)
from backend.quality.phase4_adapter import Phase4Adapter, StationAnomalySummary
from backend.quality.phase5_adapter import BottleneckSnapshot, Phase5Adapter
from backend.quality.temporal import filter_by_timestamp, validate_zero_leakage
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
from backend.quality.calibration import QualityProbabilityCalibrator, calculate_calibration_error
from backend.quality.risk import QualityRiskPolicy, compute_vehicle_risk
from backend.quality.explain import QualityExplainer
from backend.quality.service import QualityRiskService

__all__ = [
    "DefectSeverity",
    "QualityExposureLevel",
    "RecommendedAction",
    "TopRiskFactor",
    "VehicleDefectGroundTruth",
    "VehicleObservation",
    "VehicleRiskPrediction",
    "Phase4Adapter",
    "StationAnomalySummary",
    "BottleneckSnapshot",
    "Phase5Adapter",
    "filter_by_timestamp",
    "validate_zero_leakage",
    "QUALITY_FEATURE_NAMES",
    "VehicleFeaturePreprocessor",
    "extract_vehicle_features",
    "feature_dict_to_array",
    "QualityModelABC",
    "LogisticRegressionQualityModel",
    "RandomForestQualityModel",
    "XGBoostQualityModel",
    "QualityProbabilityCalibrator",
    "calculate_calibration_error",
    "QualityRiskPolicy",
    "compute_vehicle_risk",
    "QualityExplainer",
    "QualityRiskService",
]
