import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import {
  StationData,
  StationId,
  Vehicle,
  SimulationScenario,
  ScenarioId,
  AppViewMode,
  StoryScene,
  FactoryDecision,
  ExplainabilityAttribution,
  MonteCarloPass,
  TrajectoryPoint
} from '../types';
import {
  INITIAL_STATIONS,
  INITIAL_VEHICLES,
  STORY_SCENES,
  EXPLAINABILITY_DATA,
  MONTE_CARLO_PASSES,
  HISTORICAL_AND_FORECAST_TRAJECTORY,
  SIMULATION_SCENARIOS
} from '../data/factoryData';
import {
  fetchScenarios,
  fetchFactoryState,
  fetchExplainability,
  fetchUncertainty,
  fetchTrajectory
} from '../services/api';
import { soundFx } from '../utils/audioSynthesizer';

interface FactorySimulationContextType {
  // Navigation & View
  currentScene: StoryScene;
  currentSceneIndex: number;
  totalScenes: number;
  viewMode: AppViewMode;
  setViewMode: (mode: AppViewMode) => void;
  goToScene: (sceneId: number) => void;
  nextScene: () => void;
  prevScene: () => void;
  autoTourPlaying: boolean;
  toggleAutoTour: () => void;

  // Simulation Clock & Playback
  isPlaying: boolean;
  togglePlay: () => void;
  simSpeed: 1 | 2 | 5;
  setSimSpeed: (speed: 1 | 2 | 5) => void;
  simTimeSec: number;
  countdownSec: number; // 14 min countdown in seconds (840s down)
  resetSimulation: () => void;

  // Factory State
  stations: StationData[];
  vehicles: Vehicle[];
  interventionApplied: boolean;
  activeScenarioId: ScenarioId;
  setActiveScenarioId: (id: ScenarioId) => void;
  activeScenario: SimulationScenario;
  applyIntervention: (scenarioId?: ScenarioId) => void;
  revertIntervention: () => void;

  // Interactive Drawers & Modals
  selectedStation: StationData | null;
  setSelectedStation: (station: StationData | null) => void;
  selectedVehicle: Vehicle | null;
  setSelectedVehicle: (vehicle: Vehicle | null) => void;
  selectStationById: (id: StationId) => void;
  selectVehicleById: (id: string) => void;

  isWhyModalOpen: boolean;
  openWhyModal: () => void;
  closeWhyModal: () => void;

  isWhatIfModalOpen: boolean;
  openWhatIfModal: (scenarioId?: ScenarioId) => void;
  closeWhatIfModal: () => void;
  scenarios: SimulationScenario[];
  isLoadingScenarios: boolean;
  scenarioError: string | null;

  isUncertaintyModalOpen: boolean;
  openUncertaintyModal: () => void;
  closeUncertaintyModal: () => void;

  // Phase 7 Decision
  factoryDecision: FactoryDecision | null;

  // Dynamic ML / Analytics Models
  explainabilityData: ExplainabilityAttribution;
  uncertaintyData: {
    station_id?: string;
    passes: MonteCarloPass[];
    envelope?: { timeMin: number; mean: number; lowerBand90: number; upperBand90: number; stdDev: number }[];
  };
  trajectoryData: TrajectoryPoint[];

  // Audio Soundscape
  isSoundMuted: boolean;
  toggleSound: () => void;
}

const FactorySimulationContext = createContext<FactorySimulationContextType | null>(null);

export const FactorySimulationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentSceneIndex, setCurrentSceneIndex] = useState<number>(0);
  const [viewMode, setViewModeState] = useState<AppViewMode>('LIVE_FACTORY');
  const [autoTourPlaying, setAutoTourPlaying] = useState<boolean>(false);

  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [simSpeed, setSimSpeed] = useState<1 | 2 | 5>(1);
  const [simTimeSec, setSimTimeSec] = useState<number>(0);
  const [countdownSec, setCountdownSec] = useState<number>(840); // 14m 00s = 840s

  const [stations, setStations] = useState<StationData[]>(INITIAL_STATIONS);
  const [vehicles, setVehicles] = useState<Vehicle[]>(INITIAL_VEHICLES);
  const [interventionApplied, setInterventionApplied] = useState<boolean>(false);
  const [activeScenarioId, setActiveScenarioId] = useState<ScenarioId>('ADD_OPERATOR');

  const [selectedStation, setSelectedStation] = useState<StationData | null>(null);
  const [selectedVehicle, setSelectedVehicle] = useState<Vehicle | null>(null);

  const [isWhyModalOpen, setIsWhyModalOpen] = useState<boolean>(false);
  const [isWhatIfModalOpen, setIsWhatIfModalOpen] = useState<boolean>(false);
  const [isUncertaintyModalOpen, setIsUncertaintyModalOpen] = useState<boolean>(false);
  
  const [scenarios, setScenarios] = useState<SimulationScenario[]>(SIMULATION_SCENARIOS);
  const [isLoadingScenarios, setIsLoadingScenarios] = useState<boolean>(false);
  const [scenarioError, setScenarioError] = useState<string | null>(null);

  const [isSoundMuted, setIsSoundMuted] = useState<boolean>(false);
  const [factoryDecision, setFactoryDecision] = useState<FactoryDecision | null>(null);

  // Dynamic ML / Analytics state
  const [explainabilityData, setExplainabilityData] = useState<ExplainabilityAttribution>(EXPLAINABILITY_DATA);
  const [uncertaintyData, setUncertaintyData] = useState<{
    station_id?: string;
    passes: MonteCarloPass[];
    envelope?: { timeMin: number; mean: number; lowerBand90: number; upperBand90: number; stdDev: number }[];
  }>({
    passes: MONTE_CARLO_PASSES
  });
  const [trajectoryData, setTrajectoryData] = useState<TrajectoryPoint[]>(HISTORICAL_AND_FORECAST_TRAJECTORY);

  // Poll Phase 4-11 factory state from backend
  useEffect(() => {
    let active = true;
    const fetchState = async () => {
      try {
        const state = await fetchFactoryState();
        if (!active) return;
        if (state.stations && state.stations.length > 0) setStations(state.stations as StationData[]);
        if (state.vehicles && state.vehicles.length > 0) setVehicles(state.vehicles as Vehicle[]);
        if (state.decision) setFactoryDecision(state.decision);
        if (state.explainability) setExplainabilityData(state.explainability);
        if (state.uncertainty) setUncertaintyData(state.uncertainty);
        if (state.trajectory && state.trajectory.length > 0) setTrajectoryData(state.trajectory);
      } catch (err) {
        console.warn('Factory state API unavailable, using cached state:', err);
      }
    };
    
    fetchState();
    const intervalId = setInterval(fetchState, 2000);
    return () => {
      active = false;
      clearInterval(intervalId);
    };
  }, []);

  const currentScene = useMemo(() => STORY_SCENES[currentSceneIndex] || STORY_SCENES[0], [currentSceneIndex]);

  const activeScenario = useMemo(() => {
    return scenarios.find((s) => s.id === activeScenarioId) || scenarios[0] || null;
  }, [activeScenarioId, scenarios]);

  const setViewMode = useCallback((mode: AppViewMode) => {
    setViewModeState(mode);
    soundFx.playClick();
  }, []);

  const goToScene = useCallback((sceneId: number) => {
    const idx = Math.max(0, Math.min(STORY_SCENES.length - 1, sceneId - 1));
    setCurrentSceneIndex(idx);
    const targetScene = STORY_SCENES[idx];
    setViewModeState(targetScene.viewMode);
    soundFx.playScanPing();
  }, []);

  const nextScene = useCallback(() => {
    if (currentSceneIndex < STORY_SCENES.length - 1) {
      goToScene(currentSceneIndex + 2);
    } else {
      goToScene(1);
    }
  }, [currentSceneIndex, goToScene]);

  const prevScene = useCallback(() => {
    if (currentSceneIndex > 0) {
      goToScene(currentSceneIndex);
    }
  }, [currentSceneIndex, goToScene]);

  const toggleAutoTour = useCallback(() => {
    setAutoTourPlaying((prev) => !prev);
    soundFx.playClick();
  }, []);

  // Auto-tour step advancement timer
  useEffect(() => {
    if (!autoTourPlaying) return;
    const interval = setInterval(() => {
      nextScene();
    }, 12000);
    return () => clearInterval(interval);
  }, [autoTourPlaying, nextScene]);

  const togglePlay = useCallback(() => {
    setIsPlaying((prev) => !prev);
    soundFx.playClick();
  }, []);

  const toggleSound = useCallback(() => {
    setIsSoundMuted((prev) => {
      const next = !prev;
      soundFx.setMuted(next);
      return next;
    });
  }, []);

  const selectStationById = useCallback((id: StationId) => {
    const found = stations.find((s) => s.id === id);
    if (found) {
      setSelectedStation(found);
      soundFx.playScanPing();
    }
  }, [stations]);

  const selectVehicleById = useCallback((id: string) => {
    const found = vehicles.find((v) => v.id === id);
    if (found) {
      setSelectedVehicle(found);
      soundFx.playScanPing();
    }
  }, [vehicles]);

  const openWhyModal = useCallback(async () => {
    setIsWhyModalOpen(true);
    soundFx.playAlertChime();
    try {
      const stId = selectedStation?.id || 'S3';
      const dynamicExp = await fetchExplainability(stId);
      if (dynamicExp) setExplainabilityData(dynamicExp);
    } catch {
      // Fallback
    }
  }, [selectedStation]);

  const closeWhyModal = useCallback(() => {
    setIsWhyModalOpen(false);
    soundFx.playClick();
  }, []);

  const openWhatIfModal = useCallback(async (scenarioId?: ScenarioId) => {
    setIsWhatIfModalOpen(true);
    soundFx.playScanPing();

    if (scenarioId) {
      setActiveScenarioId(scenarioId);
    }

    // Try fetching fresh optimized scenarios in background
    setIsLoadingScenarios(true);
    setScenarioError(null);
    try {
      const fetchedScenarios = await fetchScenarios();
      if (fetchedScenarios && fetchedScenarios.length > 0) {
        setScenarios(fetchedScenarios);
        if (!scenarioId) {
          const best = fetchedScenarios.find((s) => s.isRecommended);
          if (best) {
            setActiveScenarioId(best.id);
          }
        }
      }
    } catch (err) {
      console.warn('Could not fetch dynamic scenarios, using local simulations:', err);
      setScenarioError(null);
    } finally {
      setIsLoadingScenarios(false);
    }
  }, []);

  const closeWhatIfModal = useCallback(() => {
    setIsWhatIfModalOpen(false);
    soundFx.playClick();
  }, []);

  const openUncertaintyModal = useCallback(async () => {
    setIsUncertaintyModalOpen(true);
    soundFx.playScanPing();
    try {
      const stId = selectedStation?.id || 'S3';
      const dynamicUnc = await fetchUncertainty(stId);
      if (dynamicUnc) setUncertaintyData(dynamicUnc);
    } catch {
      // Fallback
    }
  }, [selectedStation]);

  const closeUncertaintyModal = useCallback(() => {
    setIsUncertaintyModalOpen(false);
    soundFx.playClick();
  }, []);

  const applyIntervention = useCallback((scenarioId?: ScenarioId) => {
    const chosenScenarioId = scenarioId || activeScenarioId;
    setActiveScenarioId(chosenScenarioId);
    
    const chosenScenario = scenarios.find(s => s.id === chosenScenarioId);
    
    setInterventionApplied(true);
    soundFx.playInterventionSuccess();

    if (!chosenScenario) return;

    setStations((prev) =>
      prev.map((station) => {
        if (chosenScenario.affectedStations?.includes(station.id) || chosenScenario.bottleneckMigrated) {
            return {
                ...station,
                deviationScore: 0.05,
                telemetry: {
                  ...station.telemetry,
                  machineState: 'RUNNING'
                }
            };
        }
        return station;
      })
    );
  }, [activeScenarioId, scenarios]);

  const revertIntervention = useCallback(() => {
    setInterventionApplied(false);
    setStations(INITIAL_STATIONS);
    soundFx.playClick();
  }, []);

  const resetSimulation = useCallback(() => {
    setSimTimeSec(0);
    setCountdownSec(840);
    setInterventionApplied(false);
    setStations(INITIAL_STATIONS);
    setVehicles(INITIAL_VEHICLES);
    soundFx.playScanPing();
  }, []);

  // Main simulation tick loop
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      const deltaSec = 0.5 * simSpeed;
      setSimTimeSec((prev) => prev + deltaSec);

      // Countdown to bottleneck
      setCountdownSec((prev) => {
        if (interventionApplied) return 840;
        return Math.max(0, prev - deltaSec);
      });
    }, 500);

    return () => clearInterval(interval);
  }, [isPlaying, simSpeed, interventionApplied]);

  return (
    <FactorySimulationContext.Provider
      value={{
        currentScene,
        currentSceneIndex,
        totalScenes: STORY_SCENES.length,
        viewMode,
        setViewMode,
        goToScene,
        nextScene,
        prevScene,
        autoTourPlaying,
        toggleAutoTour,
        isPlaying,
        togglePlay,
        simSpeed,
        setSimSpeed,
        simTimeSec,
        countdownSec,
        resetSimulation,
        stations,
        vehicles,
        interventionApplied,
        activeScenarioId,
        setActiveScenarioId,
        activeScenario,
        applyIntervention,
        revertIntervention,
        selectedStation,
        setSelectedStation,
        selectedVehicle,
        setSelectedVehicle,
        selectStationById,
        selectVehicleById,
        isWhyModalOpen,
        openWhyModal,
        closeWhyModal,
        isWhatIfModalOpen,
        openWhatIfModal,
        closeWhatIfModal,
        scenarios,
        isLoadingScenarios,
        scenarioError,
        isUncertaintyModalOpen,
        openUncertaintyModal,
        closeUncertaintyModal,
        factoryDecision,
        explainabilityData,
        uncertaintyData,
        trajectoryData,
        isSoundMuted,
        toggleSound
      }}
    >
      {children}
    </FactorySimulationContext.Provider>
  );
};

export const useFactorySimulation = () => {
  const context = useContext(FactorySimulationContext);
  if (!context) {
    throw new Error('useFactorySimulation must be used within a FactorySimulationProvider');
  }
  return context;
};
