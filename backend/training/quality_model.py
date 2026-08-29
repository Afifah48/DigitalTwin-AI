from typing import Dict, Any, Optional, List
from enum import Enum
import numpy as np
from pydantic import BaseModel
from ..models.states import VehicleState, VehiclePass
from ..models.enums import StationId, ExposureLevel


class DefectCategory(str, Enum):
    ASSEMBLY_ALIGNMENT = "ASSEMBLY_ALIGNMENT"
    PAINT = "PAINT"
    POWERTRAIN = "POWERTRAIN"
    HARNESS = "HARNESS"
    INSPECTION = "INSPECTION"
    NONE = "NONE"


class DefectSeverity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    CRITICAL = "CRITICAL"


class VehicleQualityRecord(BaseModel):
    vehicle_id: str
    episode_id: str
    model: str
    vin: str
    latent_quality_stress: float
    defect_probability_ground_truth: float
    is_defective: bool
    defect_category: DefectCategory
    defect_severity: DefectSeverity
    primary_contributing_station: Optional[StationId] = None
    qa_routing_required: bool = False


class VehicleQualityEngine:
    """
    Computes latent process exposure quality stress and generates probabilistic
    ground truth defect labels without leaking future outcomes into pass features.
    """

    STATION_DEFECT_MAP = {
        StationId.S1: DefectCategory.ASSEMBLY_ALIGNMENT,
        StationId.S2: DefectCategory.PAINT,
        StationId.S3: DefectCategory.ASSEMBLY_ALIGNMENT,
        StationId.S4: DefectCategory.POWERTRAIN,
        StationId.S5: DefectCategory.HARNESS,
        StationId.S6: DefectCategory.INSPECTION,
    }

    def __init__(self, rng: Optional[np.random.Generator] = None):
        self.rng = rng if rng is not None else np.random.default_rng()

    def evaluate_vehicle_quality(
        self,
        vehicle: VehicleState,
        episode_id: str,
    ) -> VehicleQualityRecord:
        """
        Integrates multi-station process exposure stress and generates ground truth defect labels.
        """
        total_stress = 0.0
        station_stresses: Dict[StationId, float] = {}

        for p in vehicle.history:
            st_stress = 0.0
            # 1. Cycle time deviation impact
            if p.deviation_at_pass > 0.05:
                st_stress += p.deviation_at_pass * 2.0

            # 2. Specific sensor exposure stressors
            if p.torque_variance and p.torque_variance > 0.25:
                st_stress += (p.torque_variance - 0.25) * 3.5

            if p.thermal_delta and p.thermal_delta > 0.5:
                st_stress += (p.thermal_delta - 0.5) * 1.5

            # 3. Qualitative exposure level flag
            if p.exposure_flag == ExposureLevel.HIGH:
                st_stress += 1.8
            elif p.exposure_flag == ExposureLevel.MEDIUM:
                st_stress += 0.6

            station_stresses[p.station_id] = st_stress
            total_stress += st_stress

        # Add small latent baseline noise
        latent_stress = round(float(total_stress + self.rng.normal(0.05, 0.02)), 4)
        latent_stress = max(0.0, latent_stress)

        # Sigmoid mapping: baseline defect prob ~2-4% when stress=0, rising to >80% under extreme stress
        # p = 1 / (1 + exp(- (1.2 * stress - 3.2)))
        logit = 1.2 * latent_stress - 3.2
        defect_prob = float(1.0 / (1.0 + np.exp(-logit)))
        defect_prob = min(0.98, max(0.015, defect_prob))

        # Sample actual defect ground truth
        is_defective = bool(self.rng.random() < defect_prob)

        defect_cat = DefectCategory.NONE
        defect_sev = DefectSeverity.NONE
        primary_st = None

        if is_defective:
            # Find primary contributing station
            if station_stresses:
                primary_st = max(station_stresses, key=station_stresses.get)
                defect_cat = self.STATION_DEFECT_MAP.get(primary_st, DefectCategory.ASSEMBLY_ALIGNMENT)
            else:
                defect_cat = DefectCategory.ASSEMBLY_ALIGNMENT

            if defect_prob > 0.65:
                defect_sev = DefectSeverity.CRITICAL
            elif defect_prob > 0.30:
                defect_sev = DefectSeverity.MEDIUM
            else:
                defect_sev = DefectSeverity.LOW

        qa_routing = is_defective or (defect_prob > 0.25)

        return VehicleQualityRecord(
            vehicle_id=vehicle.id,
            episode_id=episode_id,
            model=vehicle.model.value if hasattr(vehicle.model, "value") else str(vehicle.model),
            vin=vehicle.vin,
            latent_quality_stress=round(latent_stress, 4),
            defect_probability_ground_truth=round(defect_prob, 4),
            is_defective=is_defective,
            defect_category=defect_cat,
            defect_severity=defect_sev,
            primary_contributing_station=primary_st,
            qa_routing_required=qa_routing,
        )
