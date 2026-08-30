import {
  SimulationScenario,
  FactoryStateResponse,
  ExplainabilityAttribution,
  MonteCarloPass,
  TrajectoryPoint
} from '../types';

const API_BASE_URL = 'http://localhost:8000';

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

export async function fetchScenarios(): Promise<SimulationScenario[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/scenarios`);
    if (!response.ok) {
      throw new Error(`Failed to fetch scenarios: HTTP ${response.status} ${response.statusText}`);
    }
    const data: ScenariosResponse = await response.json();
    if (!data.scenarios || !Array.isArray(data.scenarios)) {
      throw new Error('Invalid response structure: missing scenarios array');
    }
    return data.scenarios;
  } catch (error) {
    console.error('API Error in fetchScenarios:', error);
    throw error;
  }
}

export async function fetchFactoryState(): Promise<FactoryStateResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/factory-state`);
    if (!response.ok) {
      throw new Error(`Failed to fetch factory state: HTTP ${response.status} ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('API Error in fetchFactoryState:', error);
    throw error;
  }
}

export async function fetchExplainability(stationId: string = 'S3'): Promise<ExplainabilityAttribution> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/explainability?station_id=${stationId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch explainability: HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('API Error in fetchExplainability:', error);
    throw error;
  }
}

export async function fetchUncertainty(stationId: string = 'S3'): Promise<UncertaintyResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/uncertainty?station_id=${stationId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch uncertainty: HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('API Error in fetchUncertainty:', error);
    throw error;
  }
}

export async function fetchTrajectory(stationId: string = 'S3'): Promise<TrajectoryPoint[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/trajectory?station_id=${stationId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch trajectory: HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('API Error in fetchTrajectory:', error);
    throw error;
  }
}
