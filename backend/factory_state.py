import pandas as pd
import numpy as np
from typing import Dict, Any, List
import os

from backend.app.decision.phase4_adapter import Phase4DecisionAdapter
from backend.app.decision.phase5_adapter import Phase5DecisionAdapter
from backend.app.decision.phase6_adapter import Phase6DecisionAdapter
from backend.app.decision.service import DecisionService
from backend.quality.schemas import VehicleRiskPrediction

# Caching globals
_df_p45 = None
_df_hist = None
_df_qual = None
_phase4 = None
_phase5 = None
_phase6 = None
_latest_t = None
_stations_base = None

def get_factory_state() -> Dict[str, Any]:
    global _df_p45, _df_hist, _df_qual, _phase4, _phase5, _phase6, _latest_t, _stations_base
    
    if _df_p45 is None:
        _df_p45 = pd.read_parquet("data/phase4_phase5_integration.parquet")
        _df_hist = pd.read_parquet("data/vehicle_station_history.parquet")
        _df_qual = pd.read_parquet("data/vehicle_quality.parquet")
        
        _phase4 = Phase4DecisionAdapter()
        _phase5 = Phase5DecisionAdapter()
        
        for _, r in _df_p45.iterrows():
            d = r.to_dict()
            _phase4.ingest_prediction(d)
            _phase5.ingest_snapshot(d)
            
        _latest_t = 4000.0
        
        # Load Phase 6 (pre-calculated or mock if too slow)
        _phase6 = Phase6DecisionAdapter()
        for _, r in _df_qual.iterrows():
            is_def = int(r['is_defective'])
            prob = 0.85 if is_def else 0.15
            _phase6.ingest_prediction(VehicleRiskPrediction(
                vehicle_id=str(r['vehicle_id']),
                timestamp=float(r.get('timestamp', _latest_t)), # approx
                risk_score=prob * 100,
                defect_probability=prob,
                quality_exposure="HIGH" if is_def else "LOW",
                recommended_action="QA_INSPECTION" if is_def else "PASS_MONITOR"
            ))

    # Advance time
    _latest_t += 10.0
    if _latest_t > 4800.0:
        _latest_t = 4000.0
        


    # Run DecisionService
    svc = DecisionService(
        phase4_adapter=_phase4,
        phase5_adapter=_phase5,
        phase6_adapter=_phase6
    )
    
    # We need telemetry snapshots for the decision service. 
    # We can reconstruct it from _df_p45 at _latest_t
    latest_rows = _df_p45[_df_p45['timestamp'] == _latest_t]
    telemetry = {
        "timestamp": _latest_t,
        "stations": {}
    }
    for _, r in latest_rows.iterrows():
        sid = str(r['station_id'])
        telemetry["stations"][sid] = {
            "station_id": sid,
            "cycle_time": float(r.get('actual_cycle_time', 50.0)),
            "cycle_time_delta": float(r.get('cycle_time_delta', 0.0)),
            "vibration": float(r.get('vibration', 0.0)),
            "temperature": float(r.get('temperature', 60.0)),
            "motor_current": float(r.get('motor_current', 4.5)),
            "current_variance": float(r.get('current_variance', 0.0)),
            "queue_length": int(r.get('queue_length', 0)),
            "wip_count": int(r.get('buffer_occupancy', 0)),
            "machine_state": "RUNNING",
            "utilization": 95.0
        }
        
    decision = svc.analyze(_latest_t, [telemetry])
    
    # Build stations list mapped to UI
    p4_preds = _phase4.get_latest_station_predictions(_latest_t)
    
    stations_ui = []
    station_names = {
        "S1": "FRAMING", "S2": "PAINT", "S3": "CHASSIS MARRIAGE", 
        "S4": "POWERTRAIN", "S5": "INTERIOR & WIRING", "S6": "FINAL INSPECTION"
    }
    
    for sid in ["S1", "S2", "S3", "S4", "S5", "S6"]:
        t_data = telemetry["stations"].get(sid, {})
        p4 = p4_preds.get(sid)
        p5 = _phase5.get_station_bottleneck_info(sid, _latest_t)
        
        state = "RUNNING"
        if p4 and p4.detected:
            state = "WARNING" if p4.severity == "MEDIUM" else "CRITICAL"
        if p5 and p5.is_bottleneck:
            state = "BLOCKED" if p5.upstream_blocking_risk > 0.5 else "STARVED" if p5.downstream_starvation_risk > 0.5 else "MICRO_STOP"
            
        stations_ui.append({
            "id": sid,
            "name": station_names.get(sid, sid),
            "subTitle": "Station",
            "description": "",
            "color": "#38BDF8",
            "telemetry": {
                "cycleTime": t_data.get("cycle_time", 50.0),
                "baselineCycleTime": 50.0,
                "utilization": t_data.get("utilization", 95.0),
                "queueLength": t_data.get("queue_length", 0),
                "bufferMax": 5,
                "wip": t_data.get("wip_count", 0),
                "temperature": t_data.get("temperature", 60.0),
                "vibration": t_data.get("vibration", 0.0),
                "motorCurrent": t_data.get("motor_current", 4.5),
                "currentVariance": t_data.get("current_variance", 0.0),
                "machineState": state,
                "confidence": 90,
                "instrumentationLevel": "HIGH"
            },
            "deviationScore": t_data.get("cycle_time_delta", 0.0),
            "spatialNeighbors": [],
            "attentionWeights": {},
            "activeTooling": "",
            "sensorCount": 50,
            # phase 4/5 raw data for UI
            "p4_anomaly_score": p4.anomaly_score if p4 else 0,
            "p4_detected": p4.detected if p4 else False,
            "p5_risk_score": p5.risk_score if p5 else 0,
            "p5_persistence": p5.persistence_score if p5 else 0,
            "p5_propagation": p5.propagation_score if p5 else 0
        })
        
    vehicles_ui = []
    # get recent vehicles from history
    recent_vids = _df_hist.sort_values('entered_at', ascending=False)['vehicle_id'].unique()[:8]
    active_hist = _df_hist[_df_hist['vehicle_id'].isin(recent_vids)]
    
    p6_preds_list = _phase6.get_predictions_as_of(_latest_t)
    p6_preds = {p.vehicle_id: p for p in p6_preds_list}
    
    for _, r in active_hist.sort_values('entered_at').drop_duplicates('vehicle_id', keep='last').iterrows():
        vid = str(r['vehicle_id'])
        p6 = p6_preds.get(vid)
        vehicles_ui.append({
            "id": vid,
            "model": "NEXUS SEDAN",
            "color": "#E2E8F0",
            "colorName": "Polar Silver",
            "vin": vid,
            "currentStationId": str(r['station_id']),
            "progressInStation": 50,
            "totalTransitTime": 200,
            "qualityExposure": p6.quality_exposure if p6 else "LOW",
            "riskScore": p6.risk_score if p6 else 0,
            "predictedQualityDefectProbability": (p6.defect_probability * 100) if p6 else 0,
            "qaRoutingRequired": (p6.recommended_action == "QA_INSPECTION") if p6 else False,
            "history": []
        })
        
    return {
        "stations": stations_ui,
        "vehicles": vehicles_ui,
        "decision": decision.to_dict()
    }
