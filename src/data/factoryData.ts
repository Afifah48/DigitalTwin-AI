import {
  StationData,
  Vehicle,
  SimulationScenario,
  ExplainabilityAttribution,
  StoryScene,
  TrajectoryPoint,
  MonteCarloPass
} from '../types';

export const INITIAL_STATIONS: StationData[] = [
  {
    id: 'S1',
    name: 'FRAMING',
    subTitle: 'Robotic Underbody & Side Ring Spot Welding',
    description: '18 high-precision KUKA robotic weld arms fastening unibody floorpan and pillars to 0.05mm tolerance.',
    color: '#38BDF8', // Cyan
    activeTooling: 'KUKA KR-QUANTEC Spot Welder Cell #04',
    sensorCount: 64,
    deviationScore: 0.04,
    spatialNeighbors: ['S2'],
    attentionWeights: { S1: 0.12, S2: 0.45, S3: 0.22, S4: 0.08, S5: 0.07, S6: 0.06 },
    telemetry: {
      cycleTime: 52.4,
      baselineCycleTime: 52.0,
      utilization: 94.2,
      queueLength: 2,
      bufferMax: 5,
      wip: 3,
      temperature: 42.1,
      vibration: 1.4,
      motorCurrent: 14.2,
      currentVariance: 0.12,
      machineState: 'RUNNING',
      confidence: 96,
      instrumentationLevel: 'HIGH'
    }
  },
  {
    id: 'S2',
    name: 'PAINT',
    subTitle: 'Electrocoat, Primer & Clearcoat Robot Cells',
    description: 'Multi-stage immersion bath and 12 electrostatic rotary bell atomizers with heated drying ovens.',
    color: '#06B6D4',
    activeTooling: 'Dürr EcoBell3 High-Rotation Atomizer',
    sensorCount: 88,
    deviationScore: 0.22,
    spatialNeighbors: ['S1', 'S3'],
    attentionWeights: { S1: 0.18, S2: 0.28, S3: 0.38, S4: 0.06, S5: 0.05, S6: 0.05 },
    telemetry: {
      cycleTime: 55.8,
      baselineCycleTime: 54.0,
      utilization: 96.5,
      queueLength: 4, // filling up due to downstream S3 backup!
      bufferMax: 5,
      wip: 4,
      temperature: 78.4,
      vibration: 2.1,
      motorCurrent: 18.5,
      currentVariance: 0.45,
      machineState: 'RUNNING', // but upstream backlog pressure building
      confidence: 94,
      instrumentationLevel: 'HIGH'
    }
  },
  {
    id: 'S3',
    name: 'CHASSIS MARRIAGE',
    subTitle: 'Decking & Automated High-Torque Multi-Spindle',
    description: 'Heavy AGV lifters docking battery pack and front/rear suspension subframes to BIW body shell.',
    color: '#F59E0B', // Amber / Warning
    activeTooling: 'Atlas Copco Tensor Reversible 8-Spindle Synchronizer',
    sensorCount: 112,
    deviationScore: 0.88, // Major deviation!
    spatialNeighbors: ['S2', 'S4'],
    attentionWeights: { S1: 0.08, S2: 0.32, S3: 0.42, S4: 0.12, S5: 0.04, S6: 0.02 },
    telemetry: {
      cycleTime: 79.6, // Degrading from 54s nominal!
      baselineCycleTime: 54.0,
      utilization: 99.1,
      queueLength: 5, // Buffer at 100% capacity!
      bufferMax: 5,
      wip: 5,
      temperature: 64.8,
      vibration: 4.8, // Drifting high
      motorCurrent: 28.4, // Spindle #4 current spikes
      currentVariance: 3.85, // High variance
      machineState: 'MICRO_STOP',
      confidence: 98,
      instrumentationLevel: 'HIGH'
    }
  },
  {
    id: 'S4',
    name: 'POWERTRAIN',
    subTitle: 'High-Voltage Harness & Drive Inverter Assembly',
    description: 'Automated 800V high-voltage busbar fastening, coolant loop coupling, and inverter bus diagnostics.',
    color: '#818CF8',
    activeTooling: 'Stäubli TX2-90 Cleanroom High-Voltage Manipulator',
    sensorCount: 52,
    deviationScore: 0.35, // Starvation beginning
    spatialNeighbors: ['S3', 'S5'],
    attentionWeights: { S1: 0.04, S2: 0.06, S3: 0.58, S4: 0.22, S5: 0.06, S6: 0.04 },
    telemetry: {
      cycleTime: 49.2,
      baselineCycleTime: 51.0,
      utilization: 68.4, // Falling due to starvation!
      queueLength: 1, // Emptying out
      bufferMax: 5,
      wip: 2,
      temperature: 36.2,
      vibration: 1.1,
      motorCurrent: 11.8,
      currentVariance: 0.18,
      machineState: 'STARVED',
      confidence: 82,
      instrumentationLevel: 'MEDIUM'
    }
  },
  {
    id: 'S5',
    name: 'INTERIOR & WIRING',
    subTitle: 'Cockpit Module, Harness Loom & Acoustic Lining',
    description: 'Collaborative human-robot cell mounting instrument panel cross-car beam and floor wiring harness.',
    color: '#A78BFA',
    activeTooling: 'Universal Robots UR10e Ergonomic Lift Assist',
    sensorCount: 28, // Limited instrumentation
    deviationScore: 0.15,
    spatialNeighbors: ['S4', 'S6'],
    attentionWeights: { S1: 0.02, S2: 0.04, S3: 0.14, S4: 0.44, S5: 0.28, S6: 0.08 },
    telemetry: {
      cycleTime: 53.0,
      baselineCycleTime: 53.0,
      utilization: 74.0,
      queueLength: 1,
      bufferMax: 5,
      wip: 2,
      temperature: 24.5,
      vibration: 0.8,
      motorCurrent: 8.2,
      currentVariance: 0.25,
      machineState: 'RUNNING',
      confidence: 58, // Lower confidence due to manual/uninstrumented ops
      instrumentationLevel: 'LOW'
    }
  },
  {
    id: 'S6',
    name: 'FINAL INSPECTION',
    subTitle: 'Optical ADAS Calibration, EOL Tester & Roll Bench',
    description: 'Dynamic 3D optical laser scanning, roll-and-brake dynamometer testing, and ADAS camera matrix alignment.',
    color: '#34D399',
    activeTooling: 'Perceptron 3D HeliMetrix In-Line Metrology Station',
    sensorCount: 96,
    deviationScore: 0.08,
    spatialNeighbors: ['S5'],
    attentionWeights: { S1: 0.02, S2: 0.03, S3: 0.08, S4: 0.12, S5: 0.42, S6: 0.33 },
    telemetry: {
      cycleTime: 55.0,
      baselineCycleTime: 55.0,
      utilization: 81.0,
      queueLength: 2,
      bufferMax: 5,
      wip: 2,
      temperature: 22.8,
      vibration: 0.6,
      motorCurrent: 9.4,
      currentVariance: 0.08,
      machineState: 'RUNNING',
      confidence: 95,
      instrumentationLevel: 'HIGH'
    }
  }
];

export const INITIAL_VEHICLES: Vehicle[] = [
  {
    id: 'CAR-1040',
    model: 'APEX GT-EV',
    color: '#38BDF8',
    colorName: 'Cyber Blue',
    vin: '1G1EV40A8R8901040',
    currentStationId: 'S6',
    progressInStation: 80,
    totalTransitTime: 318,
    qualityExposure: 'LOW',
    riskScore: 6,
    predictedQualityDefectProbability: 4.2,
    qaRoutingRequired: false,
    history: [
      { stationId: 'S1', enteredAt: 0, completedAt: 52, actualCycleTime: 52, expectedCycleTime: 52, exposureFlag: 'LOW', deviationAtPass: 0.02 },
      { stationId: 'S2', enteredAt: 55, completedAt: 110, actualCycleTime: 55, expectedCycleTime: 54, exposureFlag: 'LOW', deviationAtPass: 0.05 },
      { stationId: 'S3', enteredAt: 114, completedAt: 168, actualCycleTime: 54, expectedCycleTime: 54, torqueVariance: 0.22, exposureFlag: 'LOW', deviationAtPass: 0.08 },
      { stationId: 'S4', enteredAt: 172, completedAt: 222, actualCycleTime: 50, expectedCycleTime: 51, exposureFlag: 'LOW', deviationAtPass: 0.04 },
      { stationId: 'S5', enteredAt: 226, completedAt: 279, actualCycleTime: 53, expectedCycleTime: 53, exposureFlag: 'LOW', deviationAtPass: 0.03 }
    ]
  },
  {
    id: 'CAR-1041',
    model: 'NEXUS SEDAN',
    color: '#E2E8F0',
    colorName: 'Polar Silver',
    vin: '1G1EV40A8R8901041',
    currentStationId: 'S5',
    progressInStation: 65,
    totalTransitTime: 265,
    qualityExposure: 'LOW',
    riskScore: 12,
    predictedQualityDefectProbability: 8.5,
    qaRoutingRequired: false,
    history: [
      { stationId: 'S1', enteredAt: 20, completedAt: 73, actualCycleTime: 53, expectedCycleTime: 52, exposureFlag: 'LOW', deviationAtPass: 0.03 },
      { stationId: 'S2', enteredAt: 77, completedAt: 133, actualCycleTime: 56, expectedCycleTime: 54, exposureFlag: 'LOW', deviationAtPass: 0.07 },
      { stationId: 'S3', enteredAt: 138, completedAt: 196, actualCycleTime: 58, expectedCycleTime: 54, torqueVariance: 0.48, exposureFlag: 'LOW', deviationAtPass: 0.14 },
      { stationId: 'S4', enteredAt: 201, completedAt: 251, actualCycleTime: 50, expectedCycleTime: 51, exposureFlag: 'LOW', deviationAtPass: 0.05 }
    ]
  },
  {
    id: 'CAR-1042',
    model: 'VALENCE SUV',
    color: '#94A3B8',
    colorName: 'Titanium Graphite',
    vin: '1G1EV40A8R8901042',
    currentStationId: 'S4',
    progressInStation: 40,
    totalTransitTime: 232,
    qualityExposure: 'LOW',
    riskScore: 24,
    predictedQualityDefectProbability: 18.2,
    keyAnomalyNote: 'Slight micro-delay at S3 bolt spindle indexing; torque within tolerance limits.',
    qaRoutingRequired: false,
    history: [
      { stationId: 'S1', enteredAt: 45, completedAt: 98, actualCycleTime: 53, expectedCycleTime: 52, exposureFlag: 'LOW', deviationAtPass: 0.04 },
      { stationId: 'S2', enteredAt: 102, completedAt: 159, actualCycleTime: 57, expectedCycleTime: 54, exposureFlag: 'LOW', deviationAtPass: 0.09 },
      { stationId: 'S3', enteredAt: 165, completedAt: 231, actualCycleTime: 66, expectedCycleTime: 54, torqueVariance: 1.15, exposureFlag: 'LOW', deviationAtPass: 0.28 }
    ]
  },
  {
    id: 'CAR-1043',
    model: 'APEX GT-EV',
    color: '#EF4444',
    colorName: 'Inferno Crimson',
    vin: '1G1EV40A8R8901043',
    currentStationId: 'S3',
    progressInStation: 95,
    totalTransitTime: 215,
    qualityExposure: 'MEDIUM',
    riskScore: 58,
    predictedQualityDefectProbability: 49.0,
    keyAnomalyNote: 'Spindle #4 current surge +2.4A during chassis bolt fastening sequence.',
    qaRoutingRequired: true,
    history: [
      { stationId: 'S1', enteredAt: 70, completedAt: 122, actualCycleTime: 52, expectedCycleTime: 52, exposureFlag: 'LOW', deviationAtPass: 0.03 },
      { stationId: 'S2', enteredAt: 127, completedAt: 185, actualCycleTime: 58, expectedCycleTime: 54, exposureFlag: 'LOW', deviationAtPass: 0.12 },
      { stationId: 'S3', enteredAt: 190, completedAt: 268, actualCycleTime: 78, expectedCycleTime: 54, torqueVariance: 2.84, exposureFlag: 'MEDIUM', deviationAtPass: 0.62 }
    ]
  },
  {
    id: 'CAR-1044',
    model: 'HORIZON CROSS',
    color: '#F59E0B',
    colorName: 'Solar Flare Gold',
    vin: '1G1EV40A8R8901044',
    currentStationId: 'S3',
    progressInStation: 45,
    totalTransitTime: 178,
    qualityExposure: 'HIGH',
    riskScore: 88,
    predictedQualityDefectProbability: 79.4,
    keyAnomalyNote: 'CRITICAL: Bolt #3 seating angle shifted 1.8°. S3 cycle time extended +34s. High risk of thread galling.',
    qaRoutingRequired: true,
    history: [
      { stationId: 'S1', enteredAt: 95, completedAt: 147, actualCycleTime: 52, expectedCycleTime: 52, exposureFlag: 'LOW', deviationAtPass: 0.04 },
      { stationId: 'S2', enteredAt: 152, completedAt: 212, actualCycleTime: 60, expectedCycleTime: 54, exposureFlag: 'LOW', deviationAtPass: 0.16 },
      { stationId: 'S3', enteredAt: 218, completedAt: 312, actualCycleTime: 94, expectedCycleTime: 54, torqueVariance: 4.92, exposureFlag: 'HIGH', deviationAtPass: 0.92 }
    ]
  },
  {
    id: 'CAR-1045',
    model: 'NEXUS SEDAN',
    color: '#06B6D4',
    colorName: 'Liquid Cyan',
    vin: '1G1EV40A8R8901045',
    currentStationId: 'S2',
    progressInStation: 70,
    totalTransitTime: 120,
    qualityExposure: 'MEDIUM',
    riskScore: 42,
    predictedQualityDefectProbability: 34.1,
    keyAnomalyNote: 'Buffer B23 congestion holding car in drying bay for +14s past optimal oven schedule.',
    qaRoutingRequired: false,
    history: [
      { stationId: 'S1', enteredAt: 120, completedAt: 172, actualCycleTime: 52, expectedCycleTime: 52, exposureFlag: 'LOW', deviationAtPass: 0.03 }
    ]
  },
  {
    id: 'CAR-1046',
    model: 'VALENCE SUV',
    color: '#A855F7',
    colorName: 'Obsidian Violet',
    vin: '1G1EV40A8R8901046',
    currentStationId: 'S1',
    progressInStation: 50,
    totalTransitTime: 40,
    qualityExposure: 'LOW',
    riskScore: 4,
    predictedQualityDefectProbability: 2.1,
    qaRoutingRequired: false,
    history: []
  }
];

export const HISTORICAL_AND_FORECAST_TRAJECTORY: TrajectoryPoint[] = [
  { timeOffsetMin: -60, timestampLabel: 'T-60m', baseline: 54.0, observed: 54.1, upperBand: 55.2, lowerBand: 53.0, deltaT: 0.1, isForecast: false },
  { timeOffsetMin: -50, timestampLabel: 'T-50m', baseline: 54.0, observed: 54.3, upperBand: 55.5, lowerBand: 53.1, deltaT: 0.3, isForecast: false },
  { timeOffsetMin: -40, timestampLabel: 'T-40m', baseline: 54.0, observed: 55.0, upperBand: 56.4, lowerBand: 53.6, deltaT: 1.0, isForecast: false },
  { timeOffsetMin: -30, timestampLabel: 'T-30m', baseline: 54.0, observed: 56.8, upperBand: 58.6, lowerBand: 55.0, deltaT: 2.8, isForecast: false },
  { timeOffsetMin: -20, timestampLabel: 'T-20m', baseline: 54.0, observed: 61.2, upperBand: 63.5, lowerBand: 58.9, deltaT: 7.2, isForecast: false },
  { timeOffsetMin: -10, timestampLabel: 'T-10m', baseline: 54.0, observed: 69.4, upperBand: 72.8, lowerBand: 66.0, deltaT: 15.4, isForecast: false },
  { timeOffsetMin: 0, timestampLabel: 'NOW', baseline: 54.0, observed: 79.6, upperBand: 84.1, lowerBand: 75.1, deltaT: 25.6, isForecast: false },
  // Forecasted points
  { timeOffsetMin: 5, timestampLabel: 'T+5m', baseline: 54.0, observed: 91.2, upperBand: 98.4, lowerBand: 84.0, deltaT: 37.2, isForecast: true },
  { timeOffsetMin: 10, timestampLabel: 'T+10m', baseline: 54.0, observed: 108.5, upperBand: 119.0, lowerBand: 98.0, deltaT: 54.5, isForecast: true },
  { timeOffsetMin: 14, timestampLabel: 'T+14m', baseline: 54.0, observed: 126.0, upperBand: 142.0, lowerBand: 110.0, deltaT: 72.0, isForecast: true },
  { timeOffsetMin: 20, timestampLabel: 'T+20m', baseline: 54.0, observed: 155.0, upperBand: 178.0, lowerBand: 132.0, deltaT: 101.0, isForecast: true }
];

export const EXPLAINABILITY_DATA: ExplainabilityAttribution = {
  featureAttributions: [
    {
      feature: 'Spindle #4 Motor Current Variance',
      importance: 38.4,
      delta: '+3.85 A²',
      unit: 'A²',
      impact: 'HIGH',
      description: 'Stochastic torque load oscillations during chassis subframe decking indicating gear backlash.'
    },
    {
      feature: 'S3 Cycle-Time Deviation from DES Baseline',
      importance: 29.1,
      delta: '+25.6 s',
      unit: 'sec',
      impact: 'HIGH',
      description: 'Persistent 47% elongation over Discrete Event Simulation expected benchmark for SUV chassis variants.'
    },
    {
      feature: 'Upstream Buffer B23 Ingress Velocity',
      importance: 18.7,
      delta: '4.8 / 5 vehicles',
      unit: 'queue',
      impact: 'MEDIUM',
      description: 'Paint shop S2 outputting high-batch heavy chassis without pacing modulation.'
    },
    {
      feature: 'Hydraulic Clamp Fluid Temp Delta',
      importance: 13.8,
      delta: '+12.4 °C',
      unit: '°C',
      impact: 'LOW',
      description: 'Secondary thermal rise due to extended spindle duty cycles.'
    }
  ],
  spatialAttribution: [
    {
      stationId: 'S3',
      stationName: 'Chassis Marriage',
      influenceWeight: 52,
      role: 'PRIMARY_SOURCE',
      reason: 'Root mechanical friction and torque oscillation originating inside multi-spindle deck.'
    },
    {
      stationId: 'S2',
      stationName: 'Paint Shop',
      influenceWeight: 28,
      role: 'UPSTREAM_BACKLOG',
      reason: 'Pushing unibodies into Buffer B23, creating critical pressure & blocking risk in 8 min.'
    },
    {
      stationId: 'S4',
      stationName: 'Powertrain',
      influenceWeight: 14,
      role: 'DOWNSTREAM_STARVATION',
      reason: 'Idle waiting time increasing; will run out of feeder bodies at T+11m.'
    },
    {
      stationId: 'S1',
      stationName: 'Framing',
      influenceWeight: 6,
      role: 'NEUTRAL',
      reason: 'Nominal operation, buffer B12 absorbs framing pulses normally.'
    }
  ],
  temporalAttribution: [
    {
      timeAgoMinutes: 42,
      timeLabel: 'T-42m',
      event: 'Atlas Copco Spindle #4 micro-vibration crossed 1σ threshold (2.1 mm/s).',
      anomalySeverity: 'LOW'
    },
    {
      timeAgoMinutes: 28,
      timeLabel: 'T-28m',
      event: 'VALENCE SUV batch transit cycle time jumped from 54s to 64s.',
      anomalySeverity: 'MEDIUM'
    },
    {
      timeAgoMinutes: 14,
      timeLabel: 'T-14m',
      event: 'δ(t) reached 15.4s. AI GATv2 node detected non-linear temporal momentum.',
      anomalySeverity: 'HIGH'
    },
    {
      timeAgoMinutes: 0,
      timeLabel: 'NOW (T-0)',
      event: 'AI issues 87% Bottleneck Prediction for T+14m. Upstream blocking imminent.',
      anomalySeverity: 'HIGH'
    }
  ]
};

export const SIMULATION_SCENARIOS: SimulationScenario[] = [
  {
    id: 'NO_ACTION',
    label: 'Scenario A',
    name: 'No Action (Reactive Baseline)',
    tagline: 'Maintain status quo until hard machine failure',
    description: 'System continues without intervention. S3 reaches catastrophic queue lockup at T+14m, causing severe upstream blocking at S2 and downstream line starvation at S4.',
    badgeColor: '#EF4444',
    isRecommended: false,
    throughputDeltaUPH: -14,
    bottleneckProbabilityT20: 96,
    queueLengthT20: 5,
    highRiskVehiclesT20: 16,
    estimatedCostDowntime: 142000,
    recoveryTimeMinutes: 48,
    confidenceScore: 94,
    keyActions: [
      'Line allowed to run until auto-e-stop triggers at T+14m',
      'Paint oven halts with 4 vehicles locked inside',
      'Requires emergency maintenance dispatch after stoppage'
    ],
    trajectoryPoints: [
      { timeOffsetMin: 0, timestampLabel: 'NOW', baseline: 54, observed: 79.6, upperBand: 84, lowerBand: 75, deltaT: 25.6, isForecast: false },
      { timeOffsetMin: 5, timestampLabel: 'T+5m', baseline: 54, observed: 95.0, upperBand: 104, lowerBand: 86, deltaT: 41.0, isForecast: true },
      { timeOffsetMin: 10, timestampLabel: 'T+10m', baseline: 54, observed: 118.0, upperBand: 130, lowerBand: 106, deltaT: 64.0, isForecast: true },
      { timeOffsetMin: 14, timestampLabel: 'T+14m', baseline: 54, observed: 145.0, upperBand: 162, lowerBand: 128, deltaT: 91.0, isForecast: true },
      { timeOffsetMin: 20, timestampLabel: 'T+20m', baseline: 54, observed: 180.0, upperBand: 205, lowerBand: 155, deltaT: 126.0, isForecast: true }
    ]
  },
  {
    id: 'ADD_OPERATOR',
    label: 'Scenario B',
    name: 'Assist Operator + Dynamic Tool Offset (Optimal)',
    tagline: 'Deploy cell support technician & enable spindle torque bypass',
    description: 'Directs float technician to S3 to assist bolt feed alignment and applies adaptive AI motor torque profile. Cycle time drops to 52s in 3.5 minutes with zero line stoppage.',
    badgeColor: '#10B981', // Green
    isRecommended: true,
    throughputDeltaUPH: +9,
    bottleneckProbabilityT20: 8,
    queueLengthT20: 1,
    highRiskVehiclesT20: 0,
    estimatedCostDowntime: 2400,
    recoveryTimeMinutes: 3.5,
    confidenceScore: 96,
    keyActions: [
      'Dispatch roving tech J. Miller (ID: T-882) to S3 Chassis Cell',
      'Switch Spindle #4 to adaptive micro-step torque curve',
      'Pace S2 Paint exit buffer to smooth incoming cadence'
    ],
    trajectoryPoints: [
      { timeOffsetMin: 0, timestampLabel: 'NOW', baseline: 54, observed: 79.6, upperBand: 84, lowerBand: 75, deltaT: 25.6, isForecast: false },
      { timeOffsetMin: 5, timestampLabel: 'T+5m', baseline: 54, observed: 62.0, upperBand: 66, lowerBand: 58, deltaT: 8.0, isForecast: true },
      { timeOffsetMin: 10, timestampLabel: 'T+10m', baseline: 54, observed: 53.5, upperBand: 56, lowerBand: 51, deltaT: -0.5, isForecast: true },
      { timeOffsetMin: 14, timestampLabel: 'T+14m', baseline: 54, observed: 52.0, upperBand: 54, lowerBand: 50, deltaT: -2.0, isForecast: true },
      { timeOffsetMin: 20, timestampLabel: 'T+20m', baseline: 54, observed: 51.5, upperBand: 53, lowerBand: 50, deltaT: -2.5, isForecast: true }
    ]
  },
  {
    id: 'MAINTENANCE',
    label: 'Scenario C',
    name: 'Scheduled 8-Min Micro-Stop Maintenance',
    tagline: 'Controlled short pause to calibrate spindle head',
    description: 'Proactively pauses S3 for 8 minutes during buffer clearing. Replaces Spindle #4 driver bit. Completely restores station health but causes a temporary 6 UPH dip before full recovery.',
    badgeColor: '#3B82F6',
    isRecommended: false,
    throughputDeltaUPH: -4,
    bottleneckProbabilityT20: 14,
    queueLengthT20: 2,
    highRiskVehiclesT20: 1,
    estimatedCostDowntime: 18500,
    recoveryTimeMinutes: 8.0,
    confidenceScore: 91,
    keyActions: [
      'Synchronized 8-minute micro-stoppage during buffer gap',
      'Tooling quick-swap on Spindle #4',
      'Post-calibration 100% laser verification check'
    ],
    trajectoryPoints: [
      { timeOffsetMin: 0, timestampLabel: 'NOW', baseline: 54, observed: 79.6, upperBand: 84, lowerBand: 75, deltaT: 25.6, isForecast: false },
      { timeOffsetMin: 5, timestampLabel: 'T+5m', baseline: 54, observed: 120.0, upperBand: 125, lowerBand: 115, deltaT: 66.0, isForecast: true },
      { timeOffsetMin: 10, timestampLabel: 'T+10m', baseline: 54, observed: 58.0, upperBand: 62, lowerBand: 54, deltaT: 4.0, isForecast: true },
      { timeOffsetMin: 14, timestampLabel: 'T+14m', baseline: 54, observed: 52.0, upperBand: 55, lowerBand: 49, deltaT: -2.0, isForecast: true },
      { timeOffsetMin: 20, timestampLabel: 'T+20m', baseline: 54, observed: 51.0, upperBand: 53, lowerBand: 49, deltaT: -3.0, isForecast: true }
    ]
  },
  {
    id: 'RESEQUENCING',
    label: 'Scenario D',
    name: 'Virtual Line Resequencing & Buffer Rerouting',
    tagline: 'Divert heavy SUV trims to intermediate parallel loop',
    description: 'Re-orders WIP stream by sending complex SUV chassis variants to auxiliary prep spur, feeding lighter Sedan builds into S3. Mitigates immediate bottleneck with moderate recovery speed.',
    badgeColor: '#8B5CF6',
    isRecommended: false,
    throughputDeltaUPH: +4,
    bottleneckProbabilityT20: 32,
    queueLengthT20: 3,
    highRiskVehiclesT20: 3,
    estimatedCostDowntime: 9200,
    recoveryTimeMinutes: 11.0,
    confidenceScore: 86,
    keyActions: [
      'Switch AGV dispatch table at S2 exit spur',
      'Inject 3x light Sedan bodies into S3 queue',
      'SUV chassis deferred by 12 production slots'
    ],
    trajectoryPoints: [
      { timeOffsetMin: 0, timestampLabel: 'NOW', baseline: 54, observed: 79.6, upperBand: 84, lowerBand: 75, deltaT: 25.6, isForecast: false },
      { timeOffsetMin: 5, timestampLabel: 'T+5m', baseline: 54, observed: 72.0, upperBand: 78, lowerBand: 66, deltaT: 18.0, isForecast: true },
      { timeOffsetMin: 10, timestampLabel: 'T+10m', baseline: 54, observed: 64.0, upperBand: 70, lowerBand: 58, deltaT: 10.0, isForecast: true },
      { timeOffsetMin: 14, timestampLabel: 'T+14m', baseline: 54, observed: 58.0, upperBand: 64, lowerBand: 52, deltaT: 4.0, isForecast: true },
      { timeOffsetMin: 20, timestampLabel: 'T+20m', baseline: 54, observed: 54.0, upperBand: 59, lowerBand: 49, deltaT: 0.0, isForecast: true }
    ]
  }
];

export const MONTE_CARLO_PASSES: MonteCarloPass[] = Array.from({ length: 50 }, (_, i) => {
  const seed = (i * 17 + 7) % 100;
  const spread = (seed - 50) / 50; // -1 to 1
  return {
    passId: i + 1,
    trajectory: [
      { timeMin: 0, value: 79.6 + spread * 2 },
      { timeMin: 5, value: 91.2 + spread * 7 },
      { timeMin: 10, value: 108.5 + spread * 12 },
      { timeMin: 14, value: 126.0 + spread * 18 },
      { timeMin: 20, value: 155.0 + spread * 25 }
    ]
  };
});

export const STORY_SCENES: StoryScene[] = [
  {
    id: 1,
    title: 'SCENE 1 — EXECUTIVE FACTORY OVERVIEW',
    subtitle: 'Full Line Telemetry & Discrete Vehicle Flow',
    tagline: 'WE ARE OBSERVING THE ENTIRE FACTORY, NOT JUST ONE MACHINE.',
    keyStatement: 'A modern automotive plant produces one completed vehicle every 54 seconds across connected discrete stations.',
    viewMode: 'LIVE_FACTORY',
    highlightCard: 'TELEMETRY',
    narratorScript: 'Here is the physical automotive assembly line: 6 connected stations from Framing to Final Inspection with vehicles moving sequentially through finite buffers. Every machine and car streams live high-frequency telemetry.'
  },
  {
    id: 2,
    title: 'SCENE 2 — PHYSICAL FACTORY → DIGITAL TWIN',
    subtitle: 'Cyber-Physical Synchronization',
    tagline: 'REAL-TIME SYNCHRONIZED PRODUCTION STATE',
    keyStatement: 'The Digital Twin is not merely a static 3D model. It is the real-time computational substrate for predictive intelligence.',
    viewMode: 'SYNCHRONIZED',
    highlightCard: 'TWIN_SYNC',
    narratorScript: 'Glowing cybernetic data links synchronize physical machines with computational state vectors in the Digital Twin, mirroring buffer occupancy, torque signals, and WIP in microsecond real-time.'
  },
  {
    id: 3,
    title: 'SCENE 3 — NORMAL TRAJECTORY & DEVIATION δ(t)',
    subtitle: 'Discrete Event Simulation (DES) Baseline vs Observed Drift',
    tagline: 'δ(t) = OBSERVED STATE − EXPECTED STATE',
    keyStatement: '“An unusual state is only meaningful when compared with what should normally happen in its exact operational context.”',
    viewMode: 'DIGITAL_TWIN',
    targetStation: 'S3',
    highlightCard: 'TRAJECTORY',
    narratorScript: 'Over the last 60 minutes, S3 Chassis Marriage has been subtly drifting away from its DES nominal baseline. Cycle time and motor current variance δ(t) are gradually climbing—not an instant failure, but a creeping degradation.'
  },
  {
    id: 4,
    title: 'SCENE 4 — SPATIO-TEMPORAL AI ARCHITECTURE',
    subtitle: 'GATv2 Spatial Attention + Temporal Transformer',
    tagline: 'LEARNING HOW THE PRODUCTION LINE WILL EVOLVE',
    keyStatement: 'Spatial attention captures multi-station interdependencies; Temporal attention projects cumulative momentum across time horizons.',
    viewMode: 'DIGITAL_TWIN',
    highlightCard: 'AI_GRAPH',
    narratorScript: 'Our Spatio-Temporal AI combines Graph Attention (GATv2) to understand inter-station cross-talk with a Temporal Transformer to forecast dynamic evolution, plus Vehicle-Station cross-attention.'
  },
  {
    id: 5,
    title: 'SCENE 5 — THE PREDICTION: 14-MIN ADVANCE WARNING',
    subtitle: 'Upstream Blocking & Downstream Starvation Forecast',
    tagline: '“WE DON’T PREDICT THE BOTTLENECK. WE PREDICT HOW THE LINE WILL EVOLVE.”',
    keyStatement: 'Predicting the failure 14 minutes before physical line stoppage occurs allows preemptive human-in-the-loop intervention.',
    viewMode: 'DIGITAL_TWIN',
    targetStation: 'S3',
    highlightCard: 'PREDICTION',
    narratorScript: 'S3 is still operating right now! But the AI predicts with 87% confidence that S3 will lock up in 14 minutes. Upstream S2 paint will be blocked; downstream S4 powertrain will starve.'
  },
  {
    id: 6,
    title: 'SCENE 6 — VEHICLE-LEVEL QUALITY RISK EXPOSURE',
    subtitle: 'Unified Production Disruption + Quality Assurance Index',
    tagline: 'STATION DEVIATION → VEHICLE EXPOSURE → QUALITY RISK',
    keyStatement: 'The same computational state unifies macro factory throughput prediction with micro vehicle-level defect risk estimation.',
    viewMode: 'DIGITAL_TWIN',
    highlightCard: 'VEHICLE_RISK',
    narratorScript: 'As S3 degrades, vehicles passing through accumulate exposure. CAR-1044 experienced severe torque angular shift and is flagged for automated QA inspection routing before roll-out.'
  },
  {
    id: 7,
    title: 'SCENE 7 — EXPLAINABLE AI (XAI): WHY S3?',
    subtitle: 'Spatial, Temporal, and Feature Signal Attribution',
    tagline: 'HERE IS THE MATHEMATICAL EVIDENCE BEHIND THE PREDICTION',
    keyStatement: 'Transparent attribution builds operator trust by isolating root mechanical causes from upstream noise.',
    viewMode: 'DIGITAL_TWIN',
    targetStation: 'S3',
    highlightCard: 'EXPLAIN',
    narratorScript: 'Opening explainability reveals why S3 was flagged: Spindle #4 motor current variance contributes 38.4%, cycle-time delta 29.1%, and upstream buffer pressure 18.7% with an exact chronological timeline.'
  },
  {
    id: 8,
    title: 'SCENE 8 — COUNTERFACTUAL WHAT-IF SIMULATION',
    subtitle: '4 Parallel Virtual Futures Simulated Simultaneously',
    tagline: 'WHAT HAPPENS IF WE DO NOTHING VS IF WE INTERVENE?',
    keyStatement: 'Branching the Digital Twin into multiple candidate futures evaluates corrective policies before touching a physical wrench.',
    viewMode: 'DIGITAL_TWIN',
    highlightCard: 'SIMULATION',
    narratorScript: 'We branch the Digital Twin into four parallel futures starting from this exact millisecond: Scenario A (No Action), Scenario B (Add Operator + Adaptive Torque), Scenario C (Maintenance), and Scenario D (Resequencing).'
  },
  {
    id: 9,
    title: 'SCENE 9 — AI RECOMMENDED ACTION',
    subtitle: 'Human-in-the-Loop Decision Support',
    tagline: 'ACT BEFORE THE PROBLEM OCCURS',
    keyStatement: 'Scenario B delivers +9 UPH throughput gain, eliminates quality risk, and recovers in 3.5 minutes with 96% confidence.',
    viewMode: 'DIGITAL_TWIN',
    targetStation: 'S3',
    highlightCard: 'RECOMMENDATION',
    narratorScript: 'The system recommends Scenario B: Dispatch an assist technician to S3 and adjust spindle torque curve. The operator can review, compare, and apply this directly to the live Digital Twin.'
  },
  {
    id: 10,
    title: 'SCENE 10 — DYNAMIC BOTTLENECK MIGRATION',
    subtitle: 'Continuous Re-computation & Downstream Constraint Shift',
    tagline: 'FIXING ONE BOTTLENECK CAN SHIFT THE CONSTRAINT DOWNSTREAM',
    keyStatement: 'The Digital Twin never sleeps: once S3 is cured, it detects the next emerging constraint at S4 in T+23min.',
    viewMode: 'SYNCHRONIZED',
    targetStation: 'S4',
    highlightCard: 'MIGRATION',
    narratorScript: 'When Scenario B is applied, S3 immediately normalizes. But notice: the surge volume causes S4 Powertrain to emerge as the next secondary constraint in 23 minutes. The AI continuously loops!'
  },
  {
    id: 11,
    title: 'SCENE 11 — UNCERTAINTY & CONFIDENCE ESTIMATION',
    subtitle: 'Monte Carlo Dropout (50 Passes) & Sensor Calibration',
    tagline: 'PREDICTION IS NEVER PRESENTED WITHOUT CONFIDENCE',
    keyStatement: 'Epistemic uncertainty bounds prevent over-confident actions when sensor instrumentation is sparse (e.g. S5 manual wiring).',
    viewMode: 'DIGITAL_TWIN',
    highlightCard: 'UNCERTAINTY',
    narratorScript: 'Through 50 Monte Carlo Dropout forward passes, we generate a 90% prediction envelope. Stations with sparse telemetry like S5 have wider uncertainty, ensuring operators always know the confidence level.'
  },
  {
    id: 12,
    title: 'SCENE 12 — INTEGRATED COMMAND CENTER',
    subtitle: 'The Complete Predictive Manufacturing Operating System',
    tagline: 'DIGITALTWIN.AI: PREDICT • EXPLAIN • SIMULATE • INTERVENE',
    keyStatement: '“Predict the trajectory. Explain the cause. Simulate the consequence. Intervene before the bottleneck arrives.”',
    viewMode: 'COMMAND_CENTER',
    highlightCard: 'COMMAND_CENTER',
    narratorScript: 'All 12 capabilities unified in a single high-fidelity industrial command center. 94% factory health, zero unplanned downtime, guaranteed vehicle quality.'
  }
];
