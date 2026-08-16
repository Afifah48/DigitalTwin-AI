import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import {
  StationData,
  StationId,
  Vehicle,
  SimulationScenario,
  ScenarioId,
  AppViewMode,
  StoryScene
} from '../types';
import {
  INITIAL_STATIONS,
  INITIAL_VEHICLES,
  SIMULATION_SCENARIOS,
  STORY_SCENES
} from '../data/factoryData';
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

  isUncertaintyModalOpen: boolean;
  openUncertaintyModal: () => void;
  closeUncertaintyModal: () => void;

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

  const [isSoundMuted, setIsSoundMuted] = useState<boolean>(false);

  const currentScene = useMemo(() => STORY_SCENES[currentSceneIndex] || STORY_SCENES[0], [currentSceneIndex]);

  const activeScenario = useMemo(() => {
    return SIMULATION_SCENARIOS.find((s) => s.id === activeScenarioId) || SIMULATION_SCENARIOS[1];
  }, [activeScenarioId]);

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

  const openWhyModal = useCallback(() => {
    setIsWhyModalOpen(true);
    soundFx.playAlertChime();
  }, []);

  const closeWhyModal = useCallback(() => {
    setIsWhyModalOpen(false);
    soundFx.playClick();
  }, []);

  const openWhatIfModal = useCallback((scenarioId?: ScenarioId) => {
    if (scenarioId) setActiveScenarioId(scenarioId);
    setIsWhatIfModalOpen(true);
    soundFx.playScanPing();
  }, []);

  const closeWhatIfModal = useCallback(() => {
    setIsWhatIfModalOpen(false);
    soundFx.playClick();
  }, []);

  const openUncertaintyModal = useCallback(() => {
    setIsUncertaintyModalOpen(true);
    soundFx.playScanPing();
  }, []);

  const closeUncertaintyModal = useCallback(() => {
    setIsUncertaintyModalOpen(false);
    soundFx.playClick();
  }, []);

  const applyIntervention = useCallback((scenarioId?: ScenarioId) => {
    const chosenScenario = scenarioId || activeScenarioId;
    setActiveScenarioId(chosenScenario);
    setInterventionApplied(true);
    soundFx.playInterventionSuccess();

    // Dynamically update stations based on the intervention
    setStations((prev) =>
      prev.map((station) => {
        if (station.id === 'S3') {
          return {
            ...station,
            deviationScore: 0.05,
            telemetry: {
              ...station.telemetry,
              cycleTime: 52.0,
              queueLength: 1,
              wip: 2,
              vibration: 1.2,
              motorCurrent: 14.8,
              currentVariance: 0.15,
              machineState: 'RUNNING'
            }
          };
        }
        if (station.id === 'S2') {
          // S2 backlog clears
          return {
            ...station,
            deviationScore: 0.06,
            telemetry: {
              ...station.telemetry,
              cycleTime: 54.0,
              queueLength: 2,
              wip: 2,
              machineState: 'RUNNING'
            }
          };
        }
        if (station.id === 'S4') {
          // S4 receives surge volume and becomes emerging secondary constraint!
          return {
            ...station,
            deviationScore: 0.58, // Secondary bottleneck emergence
            telemetry: {
              ...station.telemetry,
              cycleTime: 58.5,
              queueLength: 4,
              wip: 4,
              utilization: 97.8,
              machineState: 'RUNNING'
            }
          };
        }
        return station;
      })
    );
  }, [activeScenarioId]);

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
        if (interventionApplied) {
          // If intervention applied, countdown resets / is disabled
          return 840;
        }
        return Math.max(0, prev - deltaSec);
      });

      // Move vehicles smoothly through stations
      setVehicles((prevVehicles) => {
        return prevVehicles.map((vehicle) => {
          let newProgress = vehicle.progressInStation + 1.2 * simSpeed;
          let newStation = vehicle.currentStationId;
          let newHistory = [...vehicle.history];
          let newRisk = vehicle.riskScore;
          let newExposure = vehicle.qualityExposure;

          if (newProgress >= 100) {
            newProgress = 0;
            // Advance station
            if (newStation === 'S1') newStation = 'S2';
            else if (newStation === 'S2') newStation = 'S3';
            else if (newStation === 'S3') {
              newStation = 'S4';
              // If pass through S3 without intervention, lock high exposure
              if (!interventionApplied && vehicle.id === 'CAR-1044') {
                newExposure = 'HIGH';
                newRisk = 88;
              } else if (interventionApplied) {
                newExposure = 'LOW';
                newRisk = 12;
              }
            } else if (newStation === 'S4') newStation = 'S5';
            else if (newStation === 'S5') newStation = 'S6';
            else if (newStation === 'S6') newStation = 'S1'; // loop in demo
          }

          return {
            ...vehicle,
            progressInStation: newProgress,
            currentStationId: newStation,
            history: newHistory,
            riskScore: newRisk,
            qualityExposure: newExposure
          };
        });
      });

      // Subtle dynamic noise in telemetry for live realism
      setStations((prevStations) => {
        return prevStations.map((st) => {
          const noise = (Math.random() - 0.5) * 0.4;
          const currentNoise = (Math.random() - 0.5) * 0.15;
          return {
            ...st,
            telemetry: {
              ...st.telemetry,
              temperature: Number((st.telemetry.temperature + noise * 0.05).toFixed(1)),
              motorCurrent: Number((st.telemetry.motorCurrent + currentNoise).toFixed(1))
            }
          };
        });
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
        isUncertaintyModalOpen,
        openUncertaintyModal,
        closeUncertaintyModal,
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
