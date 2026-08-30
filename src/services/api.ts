import { SimulationScenario, FactoryStateResponse } from '../types';

const API_BASE_URL = 'http://localhost:8000';

export interface ScenariosResponse {
  scenarios: SimulationScenario[];
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
