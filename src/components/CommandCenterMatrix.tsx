import React from 'react';
import { useFactorySimulation } from '../context/FactorySimulationContext';
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  Cpu,
  GitBranch,
  Layers,
  LayoutGrid,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Zap,
  Clock,
  Car
} from 'lucide-react';
import { FactoryLineCanvas } from './FactoryLineCanvas';
import { TrajectoryDeviationChart } from './TrajectoryDeviationChart';
import { PredictiveBottleneckCard } from './PredictiveBottleneckCard';

export const CommandCenterMatrix: React.FC = () => {
  const {
    stations,
    vehicles,
    interventionApplied,
    openWhyModal,
    openWhatIfModal,
    openUncertaintyModal,
    selectVehicleById,
    selectStationById,
    factoryDecision,
    activeScenario
  } = useFactorySimulation();

  // Dynamic calculations
  const avgDev = stations.length > 0
    ? stations.reduce((acc, s) => acc + s.deviationScore, 0) / stations.length
    : 0.05;
  const factoryHealthScore = Math.max(70.0, Math.min(99.9, Math.round((1 - avgDev * 0.3) * 1000) / 10));

  const highRiskVehicles = vehicles.filter((v) => v.qualityExposure === 'HIGH');
  const highRiskCount = highRiskVehicles.length;

  const currentUph = interventionApplied
    ? (activeScenario?.counterfactualThroughput || 43)
    : (activeScenario?.baselineThroughput || 34);

  const uphDelta = activeScenario?.throughputDeltaUPH ?? (interventionApplied ? 9 : -8);

  const confidencePct = factoryDecision?.confidence
    ? Math.round(factoryDecision.confidence * 100)
    : 96;

  return (
    <div className="w-full space-y-5">
      
      {/* Top Executive KPI Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 font-mono">
        
        {/* Factory Health Score */}
        <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 glass-panel">
          <div className="flex items-center justify-between text-slate-400 text-[10px] mb-1">
            <span>FACTORY HEALTH</span>
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-black text-cyan-300">{factoryHealthScore}%</span>
            <span className={`text-[10px] font-bold ${factoryHealthScore > 90 ? 'text-emerald-400' : 'text-amber-400'}`}>
              {factoryHealthScore > 90 ? 'NOMINAL' : 'ATTENTION'}
            </span>
          </div>
        </div>

        {/* Current Bottleneck */}
        <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 glass-panel">
          <div className="flex items-center justify-between text-slate-400 text-[10px] mb-1">
            <span>S3 CONSTRAINT</span>
            <Zap className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-sm font-bold text-white">
            {interventionApplied ? (
              <span className="text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> S3 MANAGED
              </span>
            ) : (
              <span className="text-amber-400 flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" /> S3 PREDICTED
              </span>
            )}
          </div>
          <span className="text-[10px] text-slate-400 block mt-0.5">
            {interventionApplied ? 'Restored 52.0s' : '14 min to lockup'}
          </span>
        </div>

        {/* Next Potential Bottleneck */}
        <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 glass-panel">
          <div className="flex items-center justify-between text-slate-400 text-[10px] mb-1">
            <span>NEXT CONSTRAINT</span>
            <Clock className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="text-sm font-bold text-indigo-300">
            S4 — POWERTRAIN
          </div>
          <span className="text-[10px] text-slate-400 block mt-0.5">
            Estimated in 23 min
          </span>
        </div>

        {/* Line Throughput */}
        <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 glass-panel">
          <div className="flex items-center justify-between text-slate-400 text-[10px] mb-1">
            <span>LINE OUTPUT</span>
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-black text-emerald-400">
              {Math.round(currentUph)}
            </span>
            <span className="text-[10px] text-slate-400">UPH</span>
          </div>
          <span className="text-[10px] text-emerald-400 block">
            {uphDelta >= 0 ? `+${uphDelta}` : `${uphDelta}`} UPH {uphDelta >= 0 ? 'gained' : 'variance'}
          </span>
        </div>

        {/* Vehicle Quality Exposure */}
        <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 glass-panel">
          <div className="flex items-center justify-between text-slate-400 text-[10px] mb-1">
            <span>QUALITY EXPOSURE</span>
            <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="text-sm font-bold text-white">
            {highRiskCount === 0 ? (
              <span className="text-emerald-400">NOMINAL (0 CARS)</span>
            ) : (
              <span className="text-amber-400">FLAGGED ({highRiskCount} {highRiskCount === 1 ? 'CAR' : 'CARS'})</span>
            )}
          </div>
          <span className="text-[10px] text-slate-400 block mt-0.5">
            Automated QA Flagged
          </span>
        </div>

        {/* Twin Confidence */}
        <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 glass-panel">
          <div className="flex items-center justify-between text-slate-400 text-[10px] mb-1">
            <span>AI CONFIDENCE</span>
            <BrainCircuit className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-2xl font-black text-cyan-300">
            {confidencePct}%
          </div>
          <span className="text-[10px] text-slate-400 block">
            MC Dropout (50 passes)
          </span>
        </div>

      </div>

      {/* Main Assembly Line Canvas */}
      <FactoryLineCanvas />

      {/* Predictive Bottleneck Card */}
      <PredictiveBottleneckCard />

      {/* Dual Bottom Section: Trajectory Chart & Vehicle Risk Watchlist */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        
        {/* Left 2 Cols: Trajectory Deviation Chart */}
        <div className="lg:col-span-2">
          <TrajectoryDeviationChart />
        </div>

        {/* Right Col: Active Vehicles & Risk Watchlist */}
        <div className="bg-[#080B11] p-4 lg:p-5 rounded-2xl border border-slate-800 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800 font-mono">
              <div className="flex items-center gap-2">
                <Car className="w-4 h-4 text-cyan-400" />
                <h4 className="font-heading font-bold text-sm text-white">
                  VEHICLE RISK WATCHLIST
                </h4>
              </div>
              <span className="text-[10px] text-slate-400">Real-time Part Tracking</span>
            </div>

            <div className="space-y-2 font-mono text-xs max-h-[260px] overflow-y-auto pr-1">
              {vehicles.map((veh) => (
                <div
                  key={veh.id}
                  onClick={() => selectVehicleById(veh.id)}
                  className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800/80 hover:border-cyan-500/40 transition-all cursor-pointer flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: veh.color }} />
                    <div>
                      <div className="font-bold text-slate-200">{veh.id}</div>
                      <div className="text-[9px] text-slate-400">{veh.model} • Station {veh.currentStationId || 'Transit'}</div>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                      veh.qualityExposure === 'HIGH' ? 'bg-red-950 text-red-300 border border-red-500/30' :
                      veh.qualityExposure === 'MEDIUM' ? 'bg-amber-950 text-amber-300 border border-amber-500/30' :
                      'bg-emerald-950 text-emerald-300 border border-emerald-500/30'
                    }`}>
                      {veh.qualityExposure} RISK ({veh.riskScore}%)
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between font-mono text-[11px]">
            <button
              onClick={() => openWhatIfModal()}
              className="text-emerald-400 hover:underline font-semibold cursor-pointer"
            >
              Simulate Counterfactuals →
            </button>
            <button
              onClick={openUncertaintyModal}
              className="text-purple-400 hover:underline font-semibold cursor-pointer"
            >
              View Uncertainty Bounds →
            </button>
          </div>
        </div>

      </div>

    </div>
  );
};
