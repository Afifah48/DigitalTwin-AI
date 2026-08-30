import os
import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List

from backend.app.decision.phase4_adapter import Phase4DecisionAdapter
from backend.app.decision.phase5_adapter import Phase5DecisionAdapter
from backend.app.decision.phase6_adapter import Phase6DecisionAdapter
from backend.app.decision.service import DecisionService
from backend.quality.schemas import VehicleRiskPrediction

# Caching globals
_df_tel = None
_df_p45 = None
_df_hist = None
_df_qual = None
_phase4 = None
_phase5 = None
_phase6 = None
_latest_t = None

STATION_METADATA = {
    "S1": {
        "name": "FRAMING",
        "subTitle": "Robotic Underbody & Side Ring Spot Welding",
        "description": "18 high-precision robotic weld arms fastening unibody floorpan and pillars to 0.05mm tolerance.",
        "color": "#38BDF8",
        "baseline_cycle_time": 52.0,
        "buffer_max": 5,
        "activeTooling": "KUKA KR-QUANTEC Spot Welder Cell #04",
        "sensorCount": 64,
        "spatialNeighbors": ["S2"],
        "attentionWeights": {"S1": 0.12, "S2": 0.45, "S3": 0.22, "S4": 0.08, "S5": 0.07, "S6": 0.06}
    },
    "S2": {
        "name": "PAINT",
        "subTitle": "Electrocoat, Primer & Clearcoat Robot Cells",
        "description": "Multi-stage immersion bath and 12 electrostatic rotary bell atomizers with heated drying ovens.",
        "color": "#06B6D4",
        "baseline_cycle_time": 54.0,
        "buffer_max": 5,
        "activeTooling": "Dürr EcoBell3 High-Rotation Atomizer",
        "sensorCount": 88,
        "spatialNeighbors": ["S1", "S3"],
        "attentionWeights": {"S1": 0.18, "S2": 0.28, "S3": 0.38, "S4": 0.06, "S5": 0.05, "S6": 0.05}
    },
    "S3": {
        "name": "CHASSIS MARRIAGE",
        "subTitle": "Decking & Automated High-Torque Multi-Spindle",
        "description": "Heavy AGV lifters docking battery pack and front/rear suspension subframes to BIW body shell.",
        "color": "#F59E0B",
        "baseline_cycle_time": 54.0,
        "buffer_max": 5,
        "activeTooling": "Atlas Copco Tensor Reversible 8-Spindle Synchronizer",
        "sensorCount": 112,
        "spatialNeighbors": ["S2", "S4"],
        "attentionWeights": {"S1": 0.08, "S2": 0.32, "S3": 0.42, "S4": 0.12, "S5": 0.04, "S6": 0.02}
    },
    "S4": {
        "name": "POWERTRAIN",
        "subTitle": "High-Voltage Harness & Drive Inverter Assembly",
        "description": "Automated 800V high-voltage busbar fastening, coolant loop coupling, and inverter bus diagnostics.",
        "color": "#818CF8",
        "baseline_cycle_time": 51.0,
        "buffer_max": 5,
        "activeTooling": "Stäubli TX2-90 Cleanroom High-Voltage Manipulator",
        "sensorCount": 52,
        "spatialNeighbors": ["S3", "S5"],
        "attentionWeights": {"S1": 0.04, "S2": 0.06, "S3": 0.58, "S4": 0.22, "S5": 0.06, "S6": 0.04}
    },
    "S5": {
        "name": "INTERIOR & WIRING",
        "subTitle": "Cockpit Module, Harness Loom & Acoustic Lining",
        "description": "Collaborative human-robot cell mounting instrument panel cross-car beam and floor wiring harness.",
        "color": "#A78BFA",
        "baseline_cycle_time": 53.0,
        "buffer_max": 5,
        "activeTooling": "Universal Robots UR10e Ergonomic Lift Assist",
        "sensorCount": 28,
        "spatialNeighbors": ["S4", "S6"],
        "attentionWeights": {"S1": 0.02, "S2": 0.04, "S3": 0.14, "S4": 0.44, "S5": 0.28, "S6": 0.08}
    },
    "S6": {
        "name": "FINAL INSPECTION",
        "subTitle": "Optical ADAS Calibration, EOL Tester & Roll Bench",
        "description": "Dynamic 3D optical laser scanning, roll-and-brake dynamometer testing, and ADAS camera matrix alignment.",
        "color": "#34D399",
        "baseline_cycle_time": 55.0,
        "buffer_max": 5,
        "activeTooling": "Perceptron 3D HeliMetrix In-Line Metrology Station",
        "sensorCount": 96,
        "spatialNeighbors": ["S5"],
        "attentionWeights": {"S1": 0.02, "S2": 0.03, "S3": 0.08, "S4": 0.12, "S5": 0.42, "S6": 0.33}
    }
}

VEHICLE_COLOR_MAP = {
    "APEX GT-EV": ("#38BDF8", "Cyber Blue"),
    "NEXUS SEDAN": ("#E2E8F0", "Polar Silver"),
    "VALENCE SUV": ("#F59E0B", "Solar Gold"),
    "HORIZON CROSS": ("#A855F7", "Deep Amethyst")
}

def _init_data_if_needed():
    global _df_tel, _df_p45, _df_hist, _df_qual, _phase4, _phase5, _phase6, _latest_t
    if _df_tel is None:
        _df_tel = pd.read_parquet("data/station_telemetry.parquet")
        _df_p45 = pd.read_parquet("data/phase4_phase5_integration.parquet")
        _df_hist = pd.read_parquet("data/vehicle_station_history.parquet")
        _df_qual = pd.read_parquet("data/vehicle_quality.parquet")
        
        _phase4 = Phase4DecisionAdapter()
        _phase5 = Phase5DecisionAdapter()
        _phase6 = Phase6DecisionAdapter()
        
        ep_p45 = _df_p45[_df_p45['episode_id'] == 'EP_0001']
        for _, r in ep_p45.iterrows():
            d = r.to_dict()
            _phase4.ingest_prediction(d)
            _phase5.ingest_snapshot(d)
            
        ep_qual = _df_qual[_df_qual['episode_id'] == 'EP_0001']
        for _, r in ep_qual.iterrows():
            is_def = int(r.get('is_defective', 0))
            prob = 0.85 if is_def else 0.12
            _phase6.ingest_prediction(VehicleRiskPrediction(
                vehicle_id=str(r['vehicle_id']),
                timestamp=float(r.get('timestamp', 2400.0)),
                risk_score=prob * 100.0,
                defect_probability=prob,
                quality_exposure="HIGH" if is_def else "LOW",
                recommended_action="QA_INSPECTION" if is_def else "PASS_MONITOR"
            ))
            
        _latest_t = 2400.0

def get_factory_state() -> Dict[str, Any]:
    global _latest_t
    _init_data_if_needed()
    
    # Smooth continuous time advance in active episode EP_0001 (S4 degradation scenario)
    _latest_t += 30.0
    if _latest_t > 4500.0:
        _latest_t = 1200.0 # loop back to start of active degradation phase
        
    ep_id = "EP_0001"
    
    # 1. Fetch Station Telemetry at current timestamp
    tel_slice = _df_tel[(_df_tel['episode_id'] == ep_id) & (_df_tel['timestamp'] == _latest_t)]
    if tel_slice.empty:
        # Fallback to nearest available timestamp
        available_ts = _df_tel[_df_tel['episode_id'] == ep_id]['timestamp'].unique()
        nearest_t = min(available_ts, key=lambda x: abs(x - _latest_t))
        tel_slice = _df_tel[(_df_tel['episode_id'] == ep_id) & (_df_tel['timestamp'] == nearest_t)]

    p4_preds = _phase4.get_latest_station_predictions(_latest_t)
    
    # 2. Extract Station UI Telemetry
    stations_ui = []
    telemetry_for_decision = {"timestamp": _latest_t, "stations": {}}
    
    for sid in ["S1", "S2", "S3", "S4", "S5", "S6"]:
        meta = STATION_METADATA.get(sid, {})
        st_rows = tel_slice[tel_slice['station_id'] == sid]
        
        if not st_rows.empty:
            r = st_rows.iloc[0]
            ct = float(r.get('cycle_time', meta['baseline_cycle_time']))
            base_ct = float(r.get('baseline_cycle_time', meta['baseline_cycle_time']))
            q_len = int(r.get('queue_length', 0))
            buf_occ = int(r.get('buffer_occupancy', 0))
            wip = int(r.get('wip', q_len + (1 if ct > 0 else 0)))
            temp = float(r.get('temperature', 45.0))
            vib = float(r.get('vibration', 1.0))
            curr = float(r.get('motor_current', 14.0))
            curr_var = float(r.get('current_variance', 0.1))
            util = float(r.get('utilization', 92.0))
            is_blk = bool(r.get('is_blocked', 0))
            is_stv = bool(r.get('is_starved', 0))
        else:
            ct = meta['baseline_cycle_time']
            base_ct = meta['baseline_cycle_time']
            q_len = 2
            buf_occ = 2
            wip = 3
            temp = 45.0
            vib = 1.0
            curr = 14.0
            curr_var = 0.1
            util = 90.0
            is_blk = False
            is_stv = False

        dev_score = max(0.0, (ct - base_ct) / max(1.0, base_ct))
        p4 = p4_preds.get(sid)
        p5 = _phase5.get_station_bottleneck_info(sid, _latest_t)
        
        # Determine Machine State
        if is_blk or (sid in ['S2', 'S3'] and buf_occ >= 4 and ct <= base_ct * 1.05):
            machine_state = 'BLOCKED'
        elif is_stv or (sid in ['S5', 'S6'] and q_len == 0 and util < 85.0):
            machine_state = 'STARVED'
        elif dev_score > 0.20 or ct > base_ct * 1.20 or (p4 and p4.detected):
            machine_state = 'MICRO_STOP'
        else:
            machine_state = 'RUNNING'
            
        telemetry_for_decision["stations"][sid] = {
            "station_id": sid,
            "cycle_time": ct,
            "cycle_time_delta": ct - base_ct,
            "vibration": vib,
            "temperature": temp,
            "motor_current": curr,
            "current_variance": curr_var,
            "queue_length": q_len,
            "wip_count": wip,
            "machine_state": machine_state,
            "utilization": util
        }
        
        stations_ui.append({
            "id": sid,
            "name": meta["name"],
            "subTitle": meta["subTitle"],
            "description": meta["description"],
            "color": meta["color"],
            "telemetry": {
                "cycleTime": round(ct, 1),
                "baselineCycleTime": round(base_ct, 1),
                "utilization": round(util, 1),
                "queueLength": max(q_len, buf_occ),
                "bufferMax": meta["buffer_max"],
                "wip": wip,
                "temperature": round(temp, 1),
                "vibration": round(vib, 2),
                "motorCurrent": round(curr, 1),
                "currentVariance": round(curr_var, 2),
                "machineState": machine_state,
                "confidence": 95 if sid != "S5" else 75,
                "instrumentationLevel": "HIGH" if sid in ["S1", "S2", "S3", "S6"] else ("MEDIUM" if sid == "S4" else "LOW")
            },
            "deviationScore": round(dev_score, 2),
            "spatialNeighbors": meta["spatialNeighbors"],
            "attentionWeights": meta["attentionWeights"],
            "activeTooling": meta["activeTooling"],
            "sensorCount": meta["sensorCount"],
            "p4_anomaly_score": round(p4.anomaly_score, 3) if p4 else 0.1,
            "p4_detected": p4.detected if p4 else False,
            "p5_risk_score": round(p5.risk_score, 3) if p5 else 0.0,
            "p5_persistence": round(p5.persistence_score, 3) if p5 else 0.0,
            "p5_propagation": round(p5.propagation_score, 3) if p5 else 0.0
        })

    # 3. Dynamic Vehicle Extraction: Active inside Station & In-Buffer Queues
    ep_vh = _df_hist[_df_hist['episode_id'] == ep_id]
    vehicles_ui = []
    
    # A. In-Station Active Vehicles
    active_in_station = ep_vh[(ep_vh['entered_at'] <= _latest_t) & (ep_vh['completed_at'] >= _latest_t)]
    
    # B. In-Buffer Queued Vehicles (Finished previous station, waiting for next station)
    queued_vehicles = []
    for vid, v_group in ep_vh.groupby('vehicle_id'):
        v_group = v_group.sort_values('entered_at')
        for i in range(len(v_group) - 1):
            p_row = v_group.iloc[i]
            n_row = v_group.iloc[i+1]
            if p_row['completed_at'] <= _latest_t <= n_row['entered_at']:
                queued_vehicles.append({
                    "vehicle_id": vid,
                    "station_id": str(n_row['station_id']),
                    "entered_at": float(p_row['completed_at']),
                    "completed_at": float(n_row['entered_at']),
                    "actual_cycle_time": float(n_row['actual_cycle_time']),
                    "model": str(n_row.get('model', 'NEXUS SEDAN')),
                    "is_in_queue": True
                })

    p6_preds_list = _phase6.get_predictions_as_of(_latest_t)
    p6_preds = {p.vehicle_id: p for p in p6_preds_list}

    # Assemble Vehicle Objects
    for _, r in active_in_station.iterrows():
        vid = str(r['vehicle_id'])
        v_model = str(r.get('model', 'NEXUS SEDAN'))
        v_color, v_color_name = VEHICLE_COLOR_MAP.get(v_model, ("#E2E8F0", "Polar Silver"))
        
        ent = float(r['entered_at'])
        act_dur = float(r['actual_cycle_time'])
        prog = min(95.0, max(5.0, ((_latest_t - ent) / max(1.0, act_dur)) * 100.0))
        
        p6 = p6_preds.get(vid)
        def_prob = (p6.defect_probability * 100.0) if p6 else 12.0
        exp_level = p6.quality_exposure if p6 else "LOW"
        risk_score = round(p6.risk_score if p6 else 12.0, 1)
        qa_req = (p6.recommended_action == "QA_INSPECTION") if p6 else False
        
        vehicles_ui.append({
            "id": vid,
            "model": v_model,
            "color": v_color,
            "colorName": v_color_name,
            "vin": f"1G1EV40A8R89{vid.replace('CAR-', '')}",
            "currentStationId": str(r['station_id']),
            "progressInStation": round(prog, 0),
            "totalTransitTime": round(_latest_t - ent, 1),
            "qualityExposure": exp_level,
            "riskScore": risk_score,
            "predictedQualityDefectProbability": round(def_prob, 1),
            "qaRoutingRequired": qa_req,
            "history": []
        })

    # Add queued vehicles (limit to buffer capacity)
    for qv in queued_vehicles[:6]:
        vid = qv["vehicle_id"]
        v_model = qv["model"]
        v_color, v_color_name = VEHICLE_COLOR_MAP.get(v_model, ("#E2E8F0", "Polar Silver"))
        p6 = p6_preds.get(vid)
        def_prob = (p6.defect_probability * 100.0) if p6 else 15.0
        
        vehicles_ui.append({
            "id": vid,
            "model": v_model,
            "color": v_color,
            "colorName": v_color_name,
            "vin": f"1G1EV40A8R89{vid.replace('CAR-', '')}",
            "currentStationId": qv["station_id"],
            "progressInStation": 0,
            "totalTransitTime": round(_latest_t - qv["entered_at"], 1),
            "qualityExposure": p6.quality_exposure if p6 else "LOW",
            "riskScore": round(p6.risk_score if p6 else 15.0, 1),
            "predictedQualityDefectProbability": round(def_prob, 1),
            "qaRoutingRequired": (p6.recommended_action == "QA_INSPECTION") if p6 else False,
            "history": []
        })

    # Fallback vehicle seeding across all 6 stations if sparse
    if len(vehicles_ui) < 6:
        st_occupied = {v["currentStationId"] for v in vehicles_ui}
        for idx, sid in enumerate(["S1", "S2", "S3", "S4", "S5", "S6"]):
            if sid not in st_occupied:
                fb_vid = f"CAR-10{40 + idx}"
                fb_model = list(VEHICLE_COLOR_MAP.keys())[idx % len(VEHICLE_COLOR_MAP)]
                fb_col, fb_col_name = VEHICLE_COLOR_MAP[fb_model]
                vehicles_ui.append({
                    "id": fb_vid,
                    "model": fb_model,
                    "color": fb_col,
                    "colorName": fb_col_name,
                    "vin": f"1G1EV40A8R89{1040 + idx}",
                    "currentStationId": sid,
                    "progressInStation": 45 + (idx * 8) % 40,
                    "totalTransitTime": 200 + idx * 40,
                    "qualityExposure": "HIGH" if sid == "S4" else "LOW",
                    "riskScore": 78.0 if sid == "S4" else 8.0,
                    "predictedQualityDefectProbability": 78.0 if sid == "S4" else 8.0,
                    "qaRoutingRequired": (sid == "S4"),
                    "history": []
                })

    # 4. Synthesize Real-Time Decision Layer
    svc = DecisionService(
        phase4_adapter=_phase4,
        phase5_adapter=_phase5,
        phase6_adapter=_phase6
    )
    decision = svc.analyze(_latest_t, [telemetry_for_decision])

    return {
        "stations": stations_ui,
        "vehicles": vehicles_ui,
        "decision": decision.to_dict()
    }
