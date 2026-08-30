import numpy as np
from typing import Dict, Any, List

def generate_monte_carlo_uncertainty_passes(
    station_id: str,
    baseline_cycle_time: float = 54.0,
    current_cycle_time: float = 79.6,
    current_variance: float = 3.85,
    instrumentation_confidence: float = 95.0,
    num_passes: int = 50,
    forecast_horizons_min: List[int] = [0, 5, 10, 14, 20]
) -> Dict[str, Any]:
    """
    Generates empirical Monte Carlo stochastic forward passes representing
    epistemic and aleatoric uncertainty bounds for station cycle-time drift.
    """
    np.random.seed(42) # Deterministic base seed for consistency
    
    # Calculate noise scaling factor based on sensor instrumentation confidence
    # Low confidence (e.g. S5 manual ops) expands variance; High confidence narrows it.
    confidence_scale = max(0.5, (100.0 - instrumentation_confidence) / 10.0 + 1.0)
    noise_sigma = np.sqrt(max(0.1, current_variance)) * confidence_scale
    
    is_degraded = current_cycle_time > (baseline_cycle_time * 1.15)
    
    # Base deterministic trajectory curve
    delta_t = current_cycle_time - baseline_cycle_time
    mean_forecast = []
    
    for t_min in forecast_horizons_min:
        if t_min == 0:
            val = current_cycle_time
        else:
            if is_degraded:
                # Upward non-linear acceleration during active bottleneck propagation
                drift_factor = 1.0 + (t_min / 14.0) * (0.6 if t_min <= 14 else 0.95)
                val = baseline_cycle_time + (delta_t * drift_factor)
            else:
                # Stochastic mean-reverting nominal fluctuations
                val = baseline_cycle_time + np.sin(t_min * 0.3) * 1.5
        mean_forecast.append(val)
        
    passes = []
    horizon_values = {t: [] for t in forecast_horizons_min}
    
    for pass_idx in range(num_passes):
        # Generate correlated stochastic trajectory for this pass
        pass_trajectory = []
        pass_seed = np.random.normal(0, 1)
        
        for idx, t_min in enumerate(forecast_horizons_min):
            time_growth = 1.0 + (t_min / 10.0) * 1.5
            stochastic_noise = pass_seed * noise_sigma * time_growth + np.random.normal(0, noise_sigma * 0.4)
            pt_val = round(max(30.0, mean_forecast[idx] + stochastic_noise), 1)
            pass_trajectory.append({
                "timeMin": t_min,
                "value": pt_val
            })
            horizon_values[t_min].append(pt_val)
            
        passes.append({
            "passId": pass_idx + 1,
            "trajectory": pass_trajectory
        })
        
    # Calculate 90% Prediction Envelopes (5th and 95th percentiles)
    envelope = []
    for t_min in forecast_horizons_min:
        vals = horizon_values[t_min]
        envelope.append({
            "timeMin": t_min,
            "mean": round(float(np.mean(vals)), 1),
            "lowerBand90": round(float(np.percentile(vals, 5)), 1),
            "upperBand90": round(float(np.percentile(vals, 95)), 1),
            "stdDev": round(float(np.std(vals)), 2)
        })
        
    return {
        "station_id": station_id,
        "instrumentation_confidence": instrumentation_confidence,
        "passes_count": num_passes,
        "passes": passes,
        "envelope": envelope
    }
