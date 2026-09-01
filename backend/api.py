import os
import time
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config.factory_config import get_default_factory_config
from backend.models.enums import StationId
from backend.optimization.models import (
    OptimizationObjective,
    InterventionConstraint,
)
from backend.optimization.optimizer import InterventionOptimizer
from backend.factory_state import (
    get_factory_state,
    get_explainability_data,
    get_uncertainty_data,
    get_trajectory_data,
)


# ---------------------------------------------------------
# Frontend location
# ---------------------------------------------------------

dist_dir = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "dist",
)

index_file = os.path.join(
    dist_dir,
    "index.html",
)


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="Digital Twin AI - Predictive Cyber-Physical Manufacturing API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

allowed_origins_env = os.environ.get(
    "ALLOWED_ORIGINS",
    "*",
)

origins = [
    o.strip()
    for o in allowed_origins_env.split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Root
# ---------------------------------------------------------

@app.get("/")
def get_root():
    """
    Serve the Digital Twin frontend at the root URL when available.

    If the compiled frontend does not exist, return the API status
    response instead.
    """

    if os.path.exists(index_file):
        return FileResponse(index_file)

    return {
        "service": "Digital Twin AI API",
        "status": "online",
        "version": "1.0.0",
        "timestamp": time.time(),
        "docs": "/docs",
    }


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------

@app.get("/health")
@app.get("/api/health")
def get_health():
    """
    Liveness and readiness probe for cloud hosting platforms.
    """

    return {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": "active",
    }


# ---------------------------------------------------------
# Explainability
# ---------------------------------------------------------

@app.get("/api/explainability")
def get_explainability_endpoint(
    station_id: str = "S3",
):
    """
    Computes real-time XAI feature attributions,
    spatial attention weights, and changepoints.
    """

    return get_explainability_data(
        station_id
    )


# ---------------------------------------------------------
# Uncertainty
# ---------------------------------------------------------

@app.get("/api/uncertainty")
def get_uncertainty_endpoint(
    station_id: str = "S3",
):
    """
    Computes 50 Monte Carlo forward passes
    and 90% prediction envelopes.
    """

    return get_uncertainty_data(
        station_id
    )


# ---------------------------------------------------------
# Trajectory
# ---------------------------------------------------------

@app.get("/api/trajectory")
def get_trajectory_endpoint(
    station_id: str = "S3",
):
    """
    Computes real rolling 60-min historical trajectory
    plus 20-min DES forecasting curve.
    """

    return get_trajectory_data(
        station_id
    )


# ---------------------------------------------------------
# Scenario mapping helper
# ---------------------------------------------------------

def _map_to_scenario(
    scenario_id: str,
    label: str,
    name: str,
    tagline: str,
    description: str,
    badge_color: str,
    is_recommended: bool,
    result=None,
    action=None,
    score: float = 0.0,
) -> Dict[str, Any]:

    if result is None:

        return {
            "id": scenario_id,
            "label": label,
            "name": name,
            "tagline": tagline,
            "description": description,
            "badgeColor": badge_color,
            "isRecommended": is_recommended,
            "throughputDeltaUPH": 0.0,
            "bottleneckProbabilityT20": 0.0,
            "queueLengthT20": 0,
            "highRiskVehiclesT20": 0,
            "estimatedCostDowntime": 0.0,
            "recoveryTimeMinutes": 0.0,
            "confidenceScore": 0.0,
            "trajectoryPoints": [],
            "keyActions": [
                "Maintain status quo"
            ],
            "score": score,
        }

    tp_delta = result.throughput_delta

    q_len = (
        result.counterfactual_total_queue
    )

    cost = (
        action.cost
        if action
        else 0.0
    )

    return {
        "id": scenario_id,
        "label": label,
        "name": name,
        "tagline": tagline,
        "description": description,
        "badgeColor": badge_color,
        "isRecommended": is_recommended,

        "throughputDeltaUPH": tp_delta,

        "bottleneckProbabilityT20":
            result.counterfactual_risk * 100.0,

        "queueLengthT20": q_len,

        "highRiskVehiclesT20": 0,

        "estimatedCostDowntime": cost,

        "recoveryTimeMinutes": 0.0,

        "confidenceScore": 95.0,

        "trajectoryPoints": [],

        "keyActions": (
            [action.description]
            if action
            else []
        ),

        "score": score,

        "affectedStations": [
            s.value
            for s in result.affected_stations
        ],

        "bottleneckMigrated":
            result.bottleneck_migrated,

        "baselineThroughput":
            result.baseline_throughput,

        "counterfactualThroughput":
            result.counterfactual_throughput,

        "baselineQueue":
            result.baseline_total_queue,

        "baselineRisk":
            result.baseline_risk,

        "riskDelta":
            result.risk_delta,
    }


# ---------------------------------------------------------
# Factory State
# ---------------------------------------------------------

@app.get("/api/factory-state")
def get_factory_state_endpoint():
    """
    Aggregated factory state from Phase 4 anomaly,
    Phase 5 bottleneck, Phase 6 quality,
    and Phase 7 decision/recommendation.
    """

    return get_factory_state()


# ---------------------------------------------------------
# Scenarios
# ---------------------------------------------------------

@app.get("/api/scenarios")
def get_scenarios():
    """
    Executes Phase 9 Optimizer which in turn runs
    Phase 8 Counterfactuals.
    """

    config = get_default_factory_config()

    # Induce S4 bottleneck matching the demo baseline
    config.station_configs[
        StationId.S4
    ].baseline_cycle_time = 75.0

    constraint = InterventionConstraint(
        max_budget=300.0
    )

    objective = OptimizationObjective(
        risk_reduction_weight=100.0,
        throughput_weight=500.0,
        queue_weight=100.0,
        cost_weight=0.5,
        disruption_weight=20.0,
    )

    optimizer = InterventionOptimizer(
        base_config=config,
        objective=objective,
        constraint=constraint,
        simulation_duration=7200.0,
        seed=42,
    )

    optimization_result = (
        optimizer.optimize()
    )

    scenarios = []


    # -----------------------------------------------------
    # 1. NO ACTION
    # -----------------------------------------------------

    if optimization_result.best_intervention:

        base_res = (
            optimization_result
            .best_intervention
            .simulated_result
        )

        scenarios.append(
            {
                "id": "NO_ACTION",
                "label": "Scenario A",
                "name": "No Action (Reactive Baseline)",
                "tagline": "Maintain status quo",
                "description":
                    "System continues without intervention.",
                "badgeColor": "#EF4444",
                "isRecommended": False,

                "throughputDeltaUPH": 0.0,

                "bottleneckProbabilityT20":
                    base_res.baseline_risk * 100.0,

                "queueLengthT20":
                    base_res.baseline_total_queue,

                "highRiskVehiclesT20": 0,

                "estimatedCostDowntime": 0.0,

                "recoveryTimeMinutes": 0.0,

                "confidenceScore": 100.0,

                "trajectoryPoints": [],

                "keyActions": [
                    "No actions taken"
                ],

                "score": 0.0,

                "baselineThroughput":
                    base_res.baseline_throughput,

                "counterfactualThroughput":
                    base_res.baseline_throughput,

                "baselineQueue":
                    base_res.baseline_total_queue,

                "baselineRisk":
                    base_res.baseline_risk,

                "riskDelta": 0.0,

                "affectedStations": [],

                "bottleneckMigrated": False,
            }
        )


    # -----------------------------------------------------
    # 2. BEST INTERVENTION
    # -----------------------------------------------------

    if optimization_result.best_intervention:

        best = (
            optimization_result
            .best_intervention
        )

        scenarios.append(
            _map_to_scenario(
                scenario_id="CANDIDATE_1",
                label="Scenario B",
                name="Optimized Intervention (Best)",
                tagline=(
                    best.action
                    .action_type
                    .name
                    .replace("_", " ")
                ),
                description=best.justification,
                badge_color="#10B981",
                is_recommended=True,
                result=best.simulated_result,
                action=best.action,
                score=best.score,
            )
        )


    # -----------------------------------------------------
    # 3. ALTERNATIVE 1
    # -----------------------------------------------------

    if len(
        optimization_result.alternative_candidates
    ) > 0:

        alt1 = (
            optimization_result
            .alternative_candidates[0]
        )

        scenarios.append(
            _map_to_scenario(
                scenario_id="CANDIDATE_2",
                label="Scenario C",
                name="Alternative Option 1",
                tagline=(
                    alt1.action
                    .action_type
                    .name
                    .replace("_", " ")
                ),
                description=alt1.justification,
                badge_color="#3B82F6",
                is_recommended=False,
                result=alt1.simulated_result,
                action=alt1.action,
                score=alt1.score,
            )
        )


    # -----------------------------------------------------
    # 4. ALTERNATIVE 2
    # -----------------------------------------------------

    if len(
        optimization_result.alternative_candidates
    ) > 1:

        alt2 = (
            optimization_result
            .alternative_candidates[1]
        )

        scenarios.append(
            _map_to_scenario(
                scenario_id="CANDIDATE_3",
                label="Scenario D",
                name="Alternative Option 2",
                tagline=(
                    alt2.action
                    .action_type
                    .name
                    .replace("_", " ")
                ),
                description=alt2.justification,
                badge_color="#8B5CF6",
                is_recommended=False,
                result=alt2.simulated_result,
                action=alt2.action,
                score=alt2.score,
            )
        )

    return {
        "scenarios": scenarios
    }


# ---------------------------------------------------------
# Serve React/Vite frontend
# ---------------------------------------------------------

if os.path.exists(dist_dir):

    assets_dir = os.path.join(
        dist_dir,
        "assets",
    )

    if os.path.exists(assets_dir):
        app.mount(
            "/assets",
            StaticFiles(
                directory=assets_dir
            ),
            name="assets",
        )


    @app.get("/{full_path:path}")
    async def serve_spa_frontend(
        full_path: str,
    ):
        """
        Serve static frontend files and fall back
        to index.html for React/Vite client-side routes.
        """

        # Do not intercept API/documentation routes
        if (
            full_path.startswith("api/")
            or full_path.startswith("docs")
            or full_path.startswith("redoc")
            or full_path == "openapi.json"
            or full_path == "health"
        ):
            raise HTTPException(
                status_code=404,
                detail="Endpoint not found",
            )

        file_path = os.path.join(
            dist_dir,
            full_path,
        )

        if (
            full_path
            and os.path.exists(file_path)
            and os.path.isfile(file_path)
        ):
            return FileResponse(
                file_path
            )

        if os.path.exists(index_file):
            return FileResponse(
                index_file
            )

        raise HTTPException(
            status_code=404,
            detail="Frontend build index.html not found",
        )