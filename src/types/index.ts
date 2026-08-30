export type StationId = 'S1' | 'S2' | 'S3' | 'S4' | 'S5' | 'S6';

export type StationStatus = 'nominal' | 'warning' | 'critical' | 'starved' | 'blocked' | 'managed';

export interface StationTelemetry {
  cycleTime: number; // in seconds (nominal ~50-55s)
  baselineCycleTime: number; // DES nominal
  utilization: number; // percentage 0-100
  queueLength: number; // vehicles waiting
  bufferMax: number;
  wip: number; // work-in-progress
  temperature: number; // °C
  vibration: number; // mm/s RMS
  motorCurrent: number; // Amperes (A)
  currentVariance: number; // A^2
  machineState: 'RUNNING' | 'IDLE' | 'MICRO_STOP' | 'MAINTENANCE_REQUIRED' | 'STARVED' | 'BLOCKED';
  confidence: number; // 0-100%
  instrumentationLevel: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface StationData {
  id: StationId;
  name: string;
  subTitle: string;
  description: string;
  color: string;
  telemetry: StationTelemetry;
  deviationScore: number; // delta(t) magnitude
  spatialNeighbors: StationId[];
  attentionWeights: Record<StationId, number>; // GATv2 spatial attention weights
  activeTooling: string;
  sensorCount: number;
}

export type ExposureLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface VehicleStationPass {
  stationId: StationId;
  enteredAt: number; // timestamp in seconds
  completedAt: number;
  actualCycleTime: number;
  expectedCycleTime: number;
  torqueVariance?: number; // for S3
  thermalDelta?: number; // for S2
  exposureFlag: ExposureLevel;
  deviationAtPass: number;
}

export interface Vehicle {
  id: string; // e.g. "CAR-1042"
  model: 'APEX GT-EV' | 'NEXUS SEDAN' | 'VALENCE SUV' | 'HORIZON CROSS';
  color: string;
  colorName: string;
  vin: string;
  currentStationId: StationId | 'BUFFER_PRE' | 'FINISHED' | null;
  currentBufferIndex?: number; // 0 to 5 (between stations)
  progressInStation: number; // 0 to 100%
  totalTransitTime: number; // seconds
  history: VehicleStationPass[];
  qualityExposure: ExposureLevel;
  riskScore: number; // 0 - 100
  predictedQualityDefectProbability: number; // 0-100%
  keyAnomalyNote?: string;
  qaRoutingRequired: boolean;
}

export interface TrajectoryPoint {
  timeOffsetMin: number; // e.g. -60 to +20
  timestampLabel: string;
  baseline: number; // nominal cycle time or queue
  observed: number; // actual or forecasted
  upperBand: number; // 90% confidence upper
  lowerBand: number; // 90% confidence lower
  deltaT: number; // observed - baseline
  isForecast: boolean;
}
export type ScenarioId = string;
export interface SimulationScenario {
  id: ScenarioId;
  label: string;
  name: string;
  tagline: string;
  description: string;
  badgeColor: string;
  isRecommended: boolean;
  throughputDeltaUPH: number;
  bottleneckProbabilityT20: number;
  queueLengthT20: number;
  highRiskVehiclesT20: number;
  estimatedCostDowntime: number;
  recoveryTimeMinutes: number;
  confidenceScore: number;
  trajectoryPoints: TrajectoryPoint[];
  keyActions: string[];
  // Phase 8/9 backend fields
  affectedStations?: string[];
  bottleneckMigrated?: boolean;
  baselineThroughput?: number;
  counterfactualThroughput?: number;
  baselineQueue?: number;
  baselineRisk?: number;
  riskDelta?: number;
  score?: number;
}

export interface FactoryDecision {
  timestamp: number;
  factory_status: string;
  overall_risk: number;
  primary_issue: string | null;
  affected_stations: string[];
  affected_vehicles: string[];
  root_causes: { hypothesis_id: string; category: string; description: string; confidence: number; station_id?: string }[];
  recommended_actions: { action: string; priority: string; target: string; reason: string }[];
  confidence: number;
}

export interface FactoryStateResponse {
  stations: (StationData & {
    p4_anomaly_score?: number;
    p4_detected?: boolean;
    p5_risk_score?: number;
    p5_persistence?: number;
    p5_propagation?: number;
  })[];
  vehicles: Vehicle[];
  decision: FactoryDecision;
}


export interface ExplainabilityAttribution {
  featureAttributions: {
    feature: string;
    importance: number; // percentage
    delta: string;
    unit: string;
    impact: 'HIGH' | 'MEDIUM' | 'LOW';
    description: string;
  }[];
  spatialAttribution: {
    stationId: StationId;
    stationName: string;
    influenceWeight: number; // 0-100%
    role: 'PRIMARY_SOURCE' | 'UPSTREAM_BACKLOG' | 'DOWNSTREAM_STARVATION' | 'NEUTRAL';
    reason: string;
  }[];
  temporalAttribution: {
    timeAgoMinutes: number;
    timeLabel: string;
    event: string;
    anomalySeverity: 'LOW' | 'MEDIUM' | 'HIGH';
  }[];
}

export interface MonteCarloPass {
  passId: number;
  trajectory: { timeMin: number; value: number }[];
}

export type AppViewMode = 'LIVE_FACTORY' | 'SYNCHRONIZED' | 'DIGITAL_TWIN' | 'COMMAND_CENTER';

export interface StoryScene {
  id: number;
  title: string;
  subtitle: string;
  tagline: string;
  keyStatement: string;
  viewMode: AppViewMode;
  targetStation?: StationId;
  highlightCard?: 'TELEMETRY' | 'TWIN_SYNC' | 'TRAJECTORY' | 'AI_GRAPH' | 'PREDICTION' | 'VEHICLE_RISK' | 'EXPLAIN' | 'SIMULATION' | 'RECOMMENDATION' | 'MIGRATION' | 'UNCERTAINTY' | 'COMMAND_CENTER';
  narratorScript: string;
}
