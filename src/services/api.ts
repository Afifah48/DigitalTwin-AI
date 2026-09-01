import {
  SimulationScenario,
  FactoryStateResponse,
  ExplainabilityAttribution,
  MonteCarloPass,
  TrajectoryPoint
} from '../types';
import {
  SIMULATION_SCENARIOS,
  EXPLAINABILITY_DATA,
  MONTE_CARLO_PASSES,
  HISTORICAL_AND_FORECAST_TRAJECTORY,
  INITIAL_STATIONS,
  INITIAL_VEHICLES
} from '../data/factoryData';

// Support custom API base URL via Vite environment variable, fallback to relative path or localhost in development
const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
export const API_BASE_URL = rawBaseUrl
  ? rawBaseUrl.replace(/\/+$/, '')
  : (import.meta.env.DEV ? 'http://localhost:8000' : '');

const getEndpointUrl = (endpoint: string): string => {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${cleanEndpoint}`;
};

export interface ScenariosResponse {
  scenarios: SimulationScenario[];
}

export interface UncertaintyResponse {
  station_id: string;
  instrumentation_confidence: number;
  passes_count: number;
  passes: MonteCarloPass[];
  envelope: { timeMin: number; mean: number; lowerBand90: number; upperBand90: number; stdDev: number }[];
}

export async function checkApiHealth(): Promise<{ status: string; url: string }> {
  try {
    const response = await fetch(getEndpointUrl('/health'), { method: 'GET', signal: AbortSignal.timeout(3000) });
    if (response.ok) {
      const data = await response.json();
      return { status: 'connected', url: API_BASE_URL || window.location.origin };
    }
    return { status: 'degraded', url: API_BASE_URL || window.location.origin };
  } catch {
    return { status: 'offline', url: API_BASE_URL || 'standalone-client' };
  }
}

export async function fetchScenarios(): Promise<SimulationScenario[]> {
  try {
    const response = await fetch(getEndpointUrl('/api/scenarios'), { signal: AbortSignal.timeout(6000) });
    if (!response.ok) {
      throw new Error(`Failed to fetch scenarios: HTTP ${response.status} ${response.statusText}`);
    }
    const data: ScenariosResponse = await response.json();
    if (!data.scenarios || !Array.isArray(data.scenarios) || data.scenarios.length === 0) {
      throw new Error('Invalid response structure: missing scenarios array');
    }
    return data.scenarios;
  } catch (error) {
    console.warn('API fetchScenarios failed, using high-fidelity fallback scenarios:', error);
    return SIMULATION_SCENARIOS;
  }
}

export async function fetchFactoryState(): Promise<FactoryStateResponse> {
  try {
    const response = await fetch(getEndpointUrl('/api/factory-state'), { signal: AbortSignal.timeout(5000) });
    if (!response.ok) {
      throw new Error(`Failed to fetch factory state: HTTP ${response.status} ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.warn('API fetchFactoryState failed, using fallback factory state:', error);
    return {
      stations: INITIAL_STATIONS,
      vehicles: INITIAL_VEHICLES,
      decision: {
        timestamp: Date.now() / 1000,
        factory_status: 'WARNING',
        overall_risk: 0.88,
        primary_issue: 'S3_BOTTLENECK',
        affected_stations: ['S3', 'S2', 'S4'],
        affected_vehicles: ['CAR-1044', 'CAR-1043'],
        root_causes: [
          { hypothesis_id: 'H1', category: 'MECHANICAL', description: 'Spindle #4 current surge & torque variation', confidence: 0.94, station_id: 'S3' }
        ],
        recommended_actions: [
          { action: 'DISPATCH_TECH', priority: 'HIGH', target: 'S3', reason: 'Prevent hard stoppage at T+14m' }
        ],
        confidence: 0.92
      },
      explainability: EXPLAINABILITY_DATA,
      uncertainty: { passes: MONTE_CARLO_PASSES },
      trajectory: HISTORICAL_AND_FORECAST_TRAJECTORY
    };
  }
}

export async function fetchExplainability(stationId: string = 'S3'): Promise<ExplainabilityAttribution> {
  try {
    const response = await fetch(getEndpointUrl(`/api/explainability?station_id=${encodeURIComponent(stationId)}`), { signal: AbortSignal.timeout(5000) });
    if (!response.ok) {
      throw new Error(`Failed to fetch explainability: HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.warn('API fetchExplainability failed, using fallback explainability:', error);
    return EXPLAINABILITY_DATA;
  }
}

export async function fetchUncertainty(stationId: string = 'S3'): Promise<UncertaintyResponse> {
  try {
    const response = await fetch(getEndpointUrl(`/api/uncertainty?station_id=${encodeURIComponent(stationId)}`), { signal: AbortSignal.timeout(5000) });
    if (!response.ok) {
      throw new Error(`Failed to fetch uncertainty: HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.warn('API fetchUncertainty failed, using fallback uncertainty:', error);
    return {
      station_id: stationId,
      instrumentation_confidence: 98,
      passes_count: 50,
      passes: MONTE_CARLO_PASSES,
      envelope: []
    };
  }
}

export async function fetchTrajectory(stationId: string = 'S3'): Promise<TrajectoryPoint[]> {
  try {
    const response = await fetch(getEndpointUrl(`/api/trajectory?station_id=${encodeURIComponent(stationId)}`), { signal: AbortSignal.timeout(5000) });
    if (!response.ok) {
      throw new Error(`Failed to fetch trajectory: HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.warn('API fetchTrajectory failed, using fallback trajectory:', error);
    return HISTORICAL_AND_FORECAST_TRAJECTORY;
  }
}

